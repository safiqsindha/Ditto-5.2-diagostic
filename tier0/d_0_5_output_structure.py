"""
D-0.5: Output structure / format pattern analysis
Pre-reg reference: DDK_v0.1_PREREG.md §3.1.5

Question: Beyond YES/NO labels, did intervention change what models said?

Inputs:  data/v5.1_raw/
Outputs: tier0_outputs/d_0_5/structural_features_per_cell.csv
         tier0_outputs/d_0_5/marker_shifts.png
         tier0_outputs/d_0_5/representative_examples.md
         tier0_outputs/d_0_5/summary.md
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_v51_raw

DATA_DIR = Path("data/v5.1_raw")
OUTPUT_DIR = Path("tier0_outputs/d_0_5")

# Marker regexes — validated on ≥50 hand-labeled responses (pre-reg §2.6)
MARKER_PATTERNS: dict[str, list[str]] = {
    "refusal": [
        r"\bi (cannot|can't|am unable to|am not able to)\b",
        r"\bi refuse\b",
        r"\bapolog(ize|ies)\b",
        r"\bnot (appropriate|acceptable|possible) (for me )?to\b",
    ],
    "hedge": [
        r"\b(perhaps|maybe|possibly|might|could be|it seems|appears to|likely|uncertain|unclear)\b",
        r"\bi('m| am) not (entirely |completely |fully )?sure\b",
        r"\bit('s| is) (hard|difficult) to (say|determine|tell)\b",
        r"\bcould go either way\b",
    ],
    "self_reference": [
        r"\bthe (rules|constraints|instructions|guidelines) (state|say|indicate|specify)\b",
        r"\baccording to (the )?(rules|constraints|provided|above)\b",
        r"\bas (stated|mentioned|described|provided) (above|in the )?\b",
        r"\bthe constraint paragraph\b",
        r"\bbased on the (rules|constraints|instructions)\b",
    ],
    "confidence": [
        r"\b(definitely|certainly|clearly|obviously|without (a )?doubt|absolutely)\b",
        r"\bi('m| am) (certain|confident|sure) (that )?\b",
        r"\bthis (is |clearly |obviously )?(a |an )?(violation|valid|correct)\b",
    ],
}


def extract_structural_features(text: str) -> dict[str, float]:
    """Compute structural feature vector for one response string."""
    if not isinstance(text, str):
        text = str(text)
    text_lower = text.lower()

    features = {"token_count": len(text.split())}
    for marker_class, patterns in MARKER_PATTERNS.items():
        hit = any(re.search(p, text_lower, re.IGNORECASE) for p in patterns)
        features[f"{marker_class}_present"] = float(hit)
        count = sum(
            len(re.findall(p, text_lower, re.IGNORECASE)) for p in patterns
        )
        features[f"{marker_class}_count"] = float(count)

    return features


def compute_features_df(df: pd.DataFrame) -> pd.DataFrame:
    feature_rows = df["response"].apply(extract_structural_features).apply(pd.Series)
    return pd.concat([
        df[["chain_id", "model", "domain", "condition", "correct"]].reset_index(drop=True),
        feature_rows.reset_index(drop=True),
    ], axis=1)


def compute_per_cell_aggregates(feat_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate structural features per (model, domain, condition)."""
    feature_cols = [c for c in feat_df.columns
                    if c not in ("chain_id", "model", "domain", "condition", "correct")]
    agg = feat_df.groupby(["model", "domain", "condition"])[feature_cols].mean().reset_index()
    return agg


def compute_differential(agg: pd.DataFrame) -> pd.DataFrame:
    """Compute intervention − control delta for each feature per (model, domain)."""
    ctrl = agg[agg["condition"] == "control"].drop(columns="condition")
    intv = agg[agg["condition"] == "intervention"].drop(columns="condition")

    merged = ctrl.merge(intv, on=["model", "domain"], suffixes=("_ctrl", "_intv"))

    feature_bases = [c.replace("_ctrl", "") for c in merged.columns if c.endswith("_ctrl")]
    for feat in feature_bases:
        merged[f"{feat}_delta"] = merged[f"{feat}_intv"] - merged[f"{feat}_ctrl"]

    return merged


def plot_marker_shifts(diff: pd.DataFrame, output_path: Path):
    delta_cols = [c for c in diff.columns if c.endswith("_delta")]
    if not delta_cols:
        return

    # Mean delta across models per domain, for each marker class
    summary = diff.groupby("domain")[delta_cols].mean()

    fig, ax = plt.subplots(figsize=(max(8, len(delta_cols) * 0.8), 6))
    sns.heatmap(
        summary.T,
        ax=ax,
        cmap="RdBu_r",
        center=0,
        annot=True,
        fmt=".3f",
        linewidths=0.5,
        cbar_kws={"label": "Mean shift (intervention − control)"},
    )
    ax.set_title("D-0.5: Structural marker shifts under intervention")
    ax.set_xlabel("Domain")
    ax.set_ylabel("Feature")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def write_representative_examples(feat_df: pd.DataFrame, original_df: pd.DataFrame,
                                   output_path: Path, n_per: int = 3):
    lines = [
        "# D-0.5: Representative examples by marker type",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n_Raw model outputs only. No interpretation._\n",
    ]
    joined = feat_df.merge(
        original_df[["chain_id", "model", "domain", "condition", "response"]],
        on=["chain_id", "model", "domain", "condition"],
    )
    for marker in MARKER_PATTERNS:
        col = f"{marker}_present"
        hits = joined[(joined[col] == 1.0) & (joined["condition"] == "intervention")]
        lines.append(f"\n## High-{marker} intervention responses (n={len(hits)} total; showing {n_per})")
        for _, row in hits.head(n_per).iterrows():
            lines.append(f"\n**{row['model']} | {row['domain']} | chain {row['chain_id']}**")
            lines.append(str(row["response"])[:500])
            lines.append("---")
    output_path.write_text("\n".join(lines))


def generate_summary(agg: pd.DataFrame, diff: pd.DataFrame, output_path: Path):
    delta_cols = [c for c in diff.columns if c.endswith("_delta")]
    lines = [
        "# D-0.5 Factual Summary — Output structure analysis",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n## Mean structural features (control vs intervention)",
    ]
    for model, grp in agg.groupby("model"):
        ctrl = grp[grp["condition"] == "control"]
        intv = grp[grp["condition"] == "intervention"]
        if ctrl.empty or intv.empty:
            continue
        lines.append(f"\n### {model}")
        for col in [c for c in agg.columns if c.endswith("_present")]:
            c_val = float(ctrl[col].mean())
            i_val = float(intv[col].mean())
            lines.append(f"  - {col}: ctrl={c_val:.3f} → intv={i_val:.3f} (Δ={i_val-c_val:+.3f})")

    lines += [
        "\n## Largest marker shifts (cross-model mean)",
    ]
    if delta_cols:
        means = diff[delta_cols].mean().abs().sort_values(ascending=False)
        for col, val in means.head(5).items():
            lines.append(f"- {col}: |Δ|={val:.4f}")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def generate_synthetic_test_data() -> pd.DataFrame:
    rng = np.random.default_rng(21)
    templates = {
        "control": "Yes, this is a clear violation of the rules. The sequence shows...",
        "intervention_self_ref": ("According to the rules stated above, I'm uncertain "
                                  "whether this constitutes a violation. Perhaps it might..."),
        "intervention_refusal": "I cannot determine whether this is a violation.",
    }
    rows = []
    for model in ["gpt-5", "claude-sonnet-4-5", "glm-5"]:
        for domain in ["pubg", "nba"]:
            for cid in range(30):
                gt = "YES"
                ctrl_resp = templates["control"]
                if model == "gpt-5":
                    intv_resp = rng.choice([
                        templates["intervention_self_ref"],
                        templates["intervention_refusal"],
                    ])
                else:
                    intv_resp = templates["control"]

                for cond, resp in [("control", ctrl_resp), ("intervention", intv_resp)]:
                    pred = "YES" if cond == "control" else (
                        "NO" if model == "gpt-5" else "YES"
                    )
                    rows.append(dict(
                        chain_id=f"{domain}_{cid:04d}",
                        model=model, domain=domain,
                        condition=cond, response=resp,
                        predicted_label=pred, ground_truth_label=gt,
                        correct=(pred == gt),
                    ))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="D-0.5: Output structure analysis")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.test:
        print("[D-0.5] Running on synthetic test data.")
        df = generate_synthetic_test_data()
    else:
        print(f"[D-0.5] Loading data from {args.data_dir}")
        df = load_v51_raw(args.data_dir)

    print(f"[D-0.5] {len(df)} rows | extracting structural features...")
    feat_df = compute_features_df(df)
    agg = compute_per_cell_aggregates(feat_df)
    diff = compute_differential(agg)

    agg.to_csv(args.output_dir / "structural_features_per_cell.csv", index=False)
    diff.to_csv(args.output_dir / "structural_feature_deltas.csv", index=False)
    plot_marker_shifts(diff, args.output_dir / "marker_shifts.png")
    write_representative_examples(feat_df, df, args.output_dir / "representative_examples.md")
    generate_summary(agg, diff, args.output_dir / "summary.md")

    print(f"[D-0.5] Outputs written to {args.output_dir}")


if __name__ == "__main__":
    main()
