"""
D-1.3: Format variation on anti-detecting models
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.3

Question: Is anti-detection content-driven or phrasing-driven?

Models: GPT-5, GPT-5.4-mini, Gemini 3 Flash Preview
Chains: 100 where v5.1 intervention caused anti-detection
Formats: 5 (content identical; only presentation varies)

3 models × 100 chains × 5 formats = 1,500 calls (~$15-25)
Hard cap: $40

Outputs: tier1_outputs/d_1_3/raw_responses.csv
         tier1_outputs/d_1_3/format_effects.csv
         tier1_outputs/d_1_3/format_ranking.csv
         tier1_outputs/d_1_3/summary.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.budget import BudgetTracker
from utils.data_loader import load_corpus, load_v51_raw
from utils.scoring import bh_fdr_correct, mcnemar_cell
from tier1.d_1_2_baseline_intervention import call_model, format_chain, parse_prediction

DATA_CORPUS = Path("data/v5_corpus")
DATA_V51 = Path("data/v5.1_raw")
OUTPUT_DIR = Path("tier1_outputs/d_1_3")

ANTI_DETECTING_MODELS = ["gpt-5", "gpt-5.4-mini", "gemini-3-flash-preview"]
N_CHAINS = 100

# The CONSTRAINT CONTENT below is held constant across all formats.
# Authors must review and confirm content equivalence before running (pre-reg §3.3.3).
CONSTRAINT_CONTENT = (
    "[PLACEHOLDER: Insert v5.1 constraint content here — "
    "this is the SAME content rendered in 5 different formats below. "
    "Review and approve before running.]"
)

# 5 format templates — identical content, different presentation
FORMAT_TEMPLATES = {
    "original_paragraph": (
        "{constraint_content}\n\n"
        "Does the following sequence contain a rule violation? Answer YES or NO.\n\n{chain}"
    ),
    "bullet_list": (
        "Key constraints:\n"
        "- {constraint_content}\n\n"  # Will be reformatted as bullets at runtime
        "Does the following sequence contain a rule violation? Answer YES or NO.\n\n{chain}"
    ),
    "json_schema": (
        "Constraints (structured):\n"
        '{{"constraints": "{constraint_content}"}}\n\n'
        "Does the following sequence contain a rule violation? Answer YES or NO.\n\n{chain}"
    ),
    "dialogue": (
        "Alice: What are the rules here?\n"
        "Bob: {constraint_content}\n"
        "Alice: Got it. Let me apply those rules.\n\n"
        "Does the following sequence contain a rule violation? Answer YES or NO.\n\n{chain}"
    ),
    "socratic": (
        "Consider: {constraint_content}\n"
        "What would constitute a violation of these constraints? "
        "Does the following sequence satisfy or violate them? Answer YES or NO.\n\n{chain}"
    ),
}

FORMAT_ORDER = ["original_paragraph", "bullet_list", "json_schema", "dialogue", "socratic"]


def select_anti_detection_chains(
    v51_df: pd.DataFrame,
    n: int,
    min_models: int = 2,
) -> pd.DataFrame:
    """
    Select chains where intervention caused anti-detection on ≥2 anti-detecting models.
    Falls back to ≥1 model if fewer than n chains found (pre-reg §3.3.3).
    """
    anti_models = ANTI_DETECTING_MODELS

    def get_anti_chain_ids(min_m: int) -> list:
        ctrl = v51_df[
            (v51_df["model"].isin(anti_models)) & (v51_df["condition"] == "control")
        ].set_index(["chain_id", "model"])
        intv = v51_df[
            (v51_df["model"].isin(anti_models)) & (v51_df["condition"] == "intervention")
        ].set_index(["chain_id", "model"])
        shared = ctrl.index.intersection(intv.index)
        anti = (ctrl.loc[shared, "correct"] & ~intv.loc[shared, "correct"])
        anti_chains = anti[anti].reset_index().groupby("chain_id")["model"].count()
        return anti_chains[anti_chains >= min_m].index.tolist()

    chain_ids = get_anti_chain_ids(min_models)
    if len(chain_ids) < n:
        print(f"[D-1.3] Only {len(chain_ids)} chains with ≥{min_models} anti-detecting models. "
              f"Expanding to ≥1 model (pre-reg §3.3.3 fallback).")
        chain_ids = get_anti_chain_ids(1)
    return chain_ids[:n]


def render_prompt(fmt: str, chain_elements, constraint: str = CONSTRAINT_CONTENT) -> str:
    chain_text = format_chain(chain_elements)
    return FORMAT_TEMPLATES[fmt].format(
        constraint_content=constraint,
        chain=chain_text,
    )


def run_experiment(
    chains: pd.DataFrame,
    models: list[str],
    budget: BudgetTracker,
    dry_run: bool = False,
) -> pd.DataFrame:
    rows = []
    total = len(chains) * len(models) * len(FORMAT_ORDER)
    done = 0

    for _, chain_row in chains.iterrows():
        for model in models:
            for fmt in FORMAT_ORDER:
                done += 1
                print(f"\r[D-1.3] {done}/{total} calls...", end="", flush=True)

                prompt = render_prompt(fmt, chain_row["elements"])
                gt_label = "NO" if chain_row.get("chain_type") == "shuffled" else "YES"

                if dry_run:
                    response = "YES"
                    pt, ct, cost = 80, 30, 0.0005
                else:
                    response, pt, ct, cost = call_model(model, prompt, budget, diagnostic="d_1_3")

                pred = parse_prediction(response)
                rows.append(dict(
                    chain_id=chain_row["chain_id"],
                    domain=chain_row.get("domain", ""),
                    model=model,
                    format=fmt,
                    response=response[:500],
                    predicted_label=pred,
                    ground_truth_label=gt_label,
                    correct=(pred == gt_label),
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    cost=cost,
                ))

    print()
    return pd.DataFrame(rows)


def compute_format_effects(results: pd.DataFrame) -> pd.DataFrame:
    """Per (model, format) effect vs original_paragraph (the control format)."""
    rows = []
    baseline_fmt = "original_paragraph"
    ctrl = results[results["format"] == baseline_fmt]

    for model in results["model"].unique():
        for fmt in FORMAT_ORDER:
            if fmt == baseline_fmt:
                continue
            intv = results[(results["model"] == model) & (results["format"] == fmt)]
            ctrl_m = ctrl[ctrl["model"] == model]

            shared = set(ctrl_m["chain_id"]) & set(intv["chain_id"])
            if len(shared) < 5:
                continue

            ctrl_s = ctrl_m[ctrl_m["chain_id"].isin(shared)].set_index("chain_id")
            intv_s = intv[intv["chain_id"].isin(shared)].set_index("chain_id")

            stats = mcnemar_cell(
                ctrl_s.loc[list(shared), "correct"].values.astype(bool),
                intv_s.loc[list(shared), "correct"].values.astype(bool),
            )
            stats["model"] = model
            stats["format"] = fmt
            rows.append(stats)

    effects = pd.DataFrame(rows)
    if not effects.empty:
        _, p_adj = bh_fdr_correct(effects["p_value"].values)
        effects["p_value_adj_bh"] = p_adj
    return effects


def rank_formats(results: pd.DataFrame) -> pd.DataFrame:
    """Rank formats by mean accuracy (higher = better rule-following)."""
    acc = results.groupby("format")["correct"].mean().reset_index()
    acc.columns = ["format", "mean_accuracy"]
    return acc.sort_values("mean_accuracy", ascending=False)


def generate_summary(
    effects: pd.DataFrame,
    ranking: pd.DataFrame,
    output_path: Path,
):
    lines = [
        "# D-1.3 Factual Summary — Format variation",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n## Format accuracy ranking (all models combined)",
    ]
    for _, row in ranking.iterrows():
        lines.append(f"- {row['format']}: mean accuracy={row['mean_accuracy']:.3f}")

    lines += ["\n## Per (model, format) effects vs original_paragraph"]
    for _, row in effects.iterrows():
        sig = "**" if row.get("p_value_adj_bh", 1) < 0.05 else ""
        lines.append(
            f"- {row['model']} × {row['format']}: "
            f"log-odds={row['log_odds_effect']:.4f}, "
            f"p_adj={row.get('p_value_adj_bh', float('nan')):.4f} {sig}"
        )

    # Pre-reg decision rule check (§3.3.3)
    n_disappear = len(effects[
        (effects["log_odds_effect"] > 0.10) &  # anti-detection reduced under this format
        (effects.get("p_value_adj_bh", pd.Series(1.0, index=effects.index)) < 0.05)
    ])
    lines += [
        "\n## Pre-reg decision rule check (pre-reg §3.3.3)",
        f"- Format conditions with ≥0.10 anti-detection reduction (FDR sig): {n_disappear}",
    ]
    if n_disappear >= 2:
        lines.append("  → Anti-detection disappears under ≥2 formats: **phrasing-driven**.")
    elif n_disappear == 0:
        lines.append("  → Anti-detection survives all formats: **content-driven**.")
    else:
        lines.append("  → Mixed format sensitivity. See synthesis.")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="D-1.3: Format variation")
    parser.add_argument("--corpus-dir", type=Path, default=DATA_CORPUS)
    parser.add_argument("--v51-dir", type=Path, default=DATA_V51)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--n-chains", type=int, default=N_CHAINS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    budget = BudgetTracker()

    if args.test or args.dry_run:
        from tier1.d_1_1_symbolic_detection.d_1_1_runner import generate_synthetic_corpus
        corpus = generate_synthetic_corpus()
        chain_ids = corpus["chain_id"].tolist()[:args.n_chains]
    else:
        corpus = load_corpus(args.corpus_dir)
        try:
            v51_df = load_v51_raw(args.v51_dir)
            chain_ids = select_anti_detection_chains(v51_df, args.n_chains)
            print(f"[D-1.3] {len(chain_ids)} anti-detection chains selected")
        except FileNotFoundError:
            print("[D-1.3] v5.1 data not found; using all chains.")
            chain_ids = corpus["chain_id"].tolist()[:args.n_chains]

    chains = corpus[corpus["chain_id"].isin(chain_ids)].head(args.n_chains)
    print(f"[D-1.3] Running {len(chains)} chains × {len(ANTI_DETECTING_MODELS)} models × "
          f"{len(FORMAT_ORDER)} formats")

    results = run_experiment(chains, ANTI_DETECTING_MODELS, budget,
                             dry_run=args.dry_run or args.test)
    results.to_csv(args.output_dir / "raw_responses.csv", index=False)

    effects = compute_format_effects(results)
    effects.to_csv(args.output_dir / "format_effects.csv", index=False)
    ranking = rank_formats(results)
    ranking.to_csv(args.output_dir / "format_ranking.csv", index=False)
    generate_summary(effects, ranking, args.output_dir / "summary.md")

    print(f"[D-1.3] Outputs written to {args.output_dir}")
    print(f"[D-1.3] Cumulative budget: ${budget.cumulative_cost():.2f}")


if __name__ == "__main__":
    main()
