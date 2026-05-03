"""
D-0.1: Per-cell × per-model breakdown
Pre-reg reference: DDK_v0.1_PREREG.md §3.1.1

Question: Does v5.1's panel-level null hide cell-level signal?

Inputs:  data/v5.1_raw/
Outputs: tier0_outputs/d_0_1/effects_per_cell.csv
         tier0_outputs/d_0_1/heatmap.png
         tier0_outputs/d_0_1/cluster_dendrogram.png
         tier0_outputs/d_0_1/summary.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_v51_raw
from utils.scoring import bh_fdr_correct, mcnemar_cell

DATA_DIR = Path("data/v5.1_raw")
OUTPUT_DIR = Path("tier0_outputs/d_0_1")

# Model display order: anti-detectors first, then neutral, then pro-detectors
# Update after D-0.1 confirms family membership.
MODEL_ORDER = [
    "gpt-5",
    "gpt-5.4-mini",
    "gemini-3-flash-preview",
    "claude-sonnet-4-5",
    "qwen3.6-plus",
    "haiku-4-5",
    "glm-5",
]

DOMAIN_ORDER = ["pubg", "nba", "csgo", "rocket_league", "poker"]


def compute_cell_effects(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-(model, domain) cell effects. Pre-reg §3.1.1."""
    rows = []
    for model in df["model"].unique():
        for domain in df["domain"].unique():
            cell = df[(df["model"] == model) & (df["domain"] == domain)]
            ctrl = cell[cell["condition"] == "control"].set_index("chain_id")
            intv = cell[cell["condition"] == "intervention"].set_index("chain_id")
            shared = ctrl.index.intersection(intv.index)

            if len(shared) < 5:
                continue

            shared_list = list(shared)
            stats = mcnemar_cell(
                ctrl.loc[shared_list, "correct"].values.astype(bool),
                intv.loc[shared_list, "correct"].values.astype(bool),
            )
            stats["model"] = model
            stats["domain"] = domain
            rows.append(stats)

    effects = pd.DataFrame(rows)
    if effects.empty:
        effects["p_value_adj_bh"] = pd.Series(dtype=float)
        effects["significant_fdr05"] = pd.Series(dtype=bool)
        return effects
    sig, p_adj = bh_fdr_correct(effects["p_value"].values)
    effects["p_value_adj_bh"] = p_adj
    effects["significant_fdr05"] = sig
    return effects


def plot_heatmap(effects: pd.DataFrame, output_path: Path):
    pivot_eff = effects.pivot(index="model", columns="domain", values="log_odds_effect")
    pivot_sig = effects.pivot(index="model", columns="domain", values="significant_fdr05")

    # Respect pre-defined order; append any unexpected models/domains
    m_order = [m for m in MODEL_ORDER if m in pivot_eff.index]
    m_order += [m for m in pivot_eff.index if m not in m_order]
    d_order = [d for d in DOMAIN_ORDER if d in pivot_eff.columns]
    d_order += [d for d in pivot_eff.columns if d not in d_order]

    pivot_eff = pivot_eff.reindex(index=m_order, columns=d_order)
    pivot_sig = pivot_sig.reindex(index=m_order, columns=d_order)

    annot = pivot_sig.map(lambda x: "*" if x else "")

    fig, ax = plt.subplots(figsize=(max(8, len(d_order) * 1.4), max(6, len(m_order) * 0.9)))
    sns.heatmap(
        pivot_eff,
        ax=ax,
        cmap="RdBu_r",
        center=0,
        vmin=-2,
        vmax=2,
        annot=annot,
        fmt="",
        linewidths=0.5,
        cbar_kws={"label": "Log-odds effect (intervention − control)"},
    )
    ax.set_title("D-0.1: Per-cell log-odds effects  (* = FDR 5% significant)")
    ax.set_xlabel("Domain")
    ax.set_ylabel("Model")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_cluster_dendrogram(effects: pd.DataFrame, output_path: Path):
    pivot = effects.pivot(index="model", columns="domain", values="log_odds_effect").fillna(0)
    if pivot.shape[0] < 2:
        return
    Z = linkage(pivot.values, method="ward")
    fig, ax = plt.subplots(figsize=(10, max(4, len(pivot) * 0.5)))
    dendrogram(Z, labels=pivot.index.tolist(), orientation="left", ax=ax)
    ax.set_title("D-0.1: Model clustering by cell effect profile (Ward linkage)")
    ax.set_xlabel("Distance")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def generate_summary(effects: pd.DataFrame, output_path: Path):
    """Factual auto-summary — no interpretation. Pre-reg §4.4."""
    n_cells = len(effects)
    n_sig = int(effects["significant_fdr05"].sum())
    n_anti = int((effects["significant_fdr05"] & (effects["log_odds_effect"] < 0)).sum())
    n_pro = int((effects["significant_fdr05"] & (effects["log_odds_effect"] > 0)).sum())
    median_eff = effects["log_odds_effect"].median()

    most_anti_idx = effects["log_odds_effect"].idxmin()
    most_anti = effects.loc[most_anti_idx]

    lines = [
        "# D-0.1 Factual Summary — Per-cell breakdown",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n## Cell counts",
        f"- Total cells analyzed: {n_cells}",
        f"- Cells significant at FDR 5%: {n_sig} / {n_cells}",
        f"  - Anti-detecting (log-odds < 0): {n_anti}",
        f"  - Pro-detecting (log-odds > 0): {n_pro}",
        "\n## Effect magnitudes",
        f"- Median log-odds effect (all cells): {median_eff:.4f}",
        f"- Largest anti-detecting effect: {most_anti['log_odds_effect']:.4f}"
        f"  ({most_anti['model']}, {most_anti['domain']})",
        "\n## Per-model breakdown",
    ]
    for model, grp in effects.groupby("model"):
        n_sig_m = int(grp["significant_fdr05"].sum())
        med = grp["log_odds_effect"].median()
        lines.append(f"- {model}: {n_sig_m}/{len(grp)} cells significant, median={med:.4f}")

    lines += ["\n## Per-domain breakdown"]
    for domain, grp in effects.groupby("domain"):
        n_sig_d = int(grp["significant_fdr05"].sum())
        med = grp["log_odds_effect"].median()
        lines.append(f"- {domain}: {n_sig_d}/{len(grp)} cells significant, median={med:.4f}")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation is deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def generate_synthetic_test_data() -> pd.DataFrame:
    """
    Synthetic v5.1-shaped data with known signal.
    gpt-5 anti-detects on pubg+nba; glm-5 pro-detects everywhere.
    Used for --test mode.
    """
    rng = np.random.default_rng(42)
    models = ["gpt-5", "claude-sonnet-4-5", "glm-5"]
    domains = ["pubg", "nba", "csgo", "rocket_league", "poker"]
    n_chains = 50
    rows = []

    for model in models:
        for domain in domains:
            for cid in range(n_chains):
                gt = rng.choice(["YES", "NO"])
                if model == "gpt-5" and domain in ("pubg", "nba"):
                    ctrl_p, intv_p = 0.80, 0.40
                elif model == "glm-5":
                    ctrl_p, intv_p = 0.55, 0.78
                else:
                    ctrl_p, intv_p = 0.65, 0.65

                for cond, p in [("control", ctrl_p), ("intervention", intv_p)]:
                    correct = rng.random() < p
                    pred = gt if correct else ("NO" if gt == "YES" else "YES")
                    rows.append(dict(
                        chain_id=f"{domain}_{cid:04d}",
                        model=model,
                        domain=domain,
                        condition=cond,
                        response=f"Synthetic response for chain {cid}",
                        predicted_label=pred,
                        ground_truth_label=gt,
                        correct=(pred == gt),
                    ))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="D-0.1: Per-cell breakdown")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--test", action="store_true", help="Run on synthetic data")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.test:
        print("[D-0.1] Running on synthetic test data.")
        df = generate_synthetic_test_data()
    else:
        print(f"[D-0.1] Loading data from {args.data_dir}")
        df = load_v51_raw(args.data_dir)

    print(f"[D-0.1] {len(df)} rows | "
          f"{df['model'].nunique()} models | {df['domain'].nunique()} domains")

    effects = compute_cell_effects(df)
    print(f"[D-0.1] {len(effects)} cells computed; "
          f"{int(effects['significant_fdr05'].sum())} significant at FDR 5%")

    effects.to_csv(args.output_dir / "effects_per_cell.csv", index=False)
    plot_heatmap(effects, args.output_dir / "heatmap.png")
    plot_cluster_dendrogram(effects, args.output_dir / "cluster_dendrogram.png")
    generate_summary(effects, args.output_dir / "summary.md")

    print(f"[D-0.1] Outputs written to {args.output_dir}")


if __name__ == "__main__":
    main()
