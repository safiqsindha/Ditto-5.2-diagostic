"""
D-1.4: v1 corpus replay under v5.1 methodology
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.4

Question: Is v5.1's null methodology-specific or corpus-specific?

Models: Claude Sonnet 4.5, Claude Haiku 4.5
Corpus: v1's 1,200 Pokémon chains
Conditions: control, v5.1 intervention

2 models × 1,200 chains × 2 conditions = 4,800 calls (~$10-20)
Hard cap: $30

Comparison baseline:
  v1 original gaps: Sonnet=+0.131, Haiku=+0.066

Outputs: tier1_outputs/d_1_4/raw_responses.csv
         tier1_outputs/d_1_4/effects_per_model.csv
         tier1_outputs/d_1_4/comparison_to_v1.csv
         tier1_outputs/d_1_4/summary.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.budget import BudgetTracker
from utils.data_loader import load_corpus
from utils.scoring import mcnemar_cell
from tier1.d_1_2_baseline_intervention import call_model, format_chain, parse_prediction

DATA_DIR = Path("data/v1_corpus")
OUTPUT_DIR = Path("tier1_outputs/d_1_4")

MODELS = ["claude-sonnet-4-5", "claude-haiku-4-5"]

# v1 original effects (log-odds approximated from reported accuracy gaps)
# Sonnet gap: +0.131 accuracy → log-odds ≈ +0.524
# Haiku gap: +0.066 accuracy → log-odds ≈ +0.264
V1_ORIGINAL_EFFECTS = {
    "claude-sonnet-4-5": {"accuracy_gap": 0.131, "log_odds_approx": 0.524},
    "claude-haiku-4-5": {"accuracy_gap": 0.066, "log_odds_approx": 0.264},
}

# v5.1 intervention prompt — adapted minimally for Pokémon domain
# CRITICAL: Document any adaptation precisely (pre-reg §3.3.4)
# Authors must review this adaptation before running.
INTERVENTION_ADAPTATION_NOTE = (
    "Adapted from v5.1 constraint paragraph: replaced game-domain references "
    "with 'Pokémon battle' references. Exact wording change documented here. "
    "[PLACEHOLDER: fill in exact adaptation when v5.1 prompt wording is confirmed]"
)

PROMPTS = {
    "control": (
        "Does the following Pokémon battle sequence contain a rule violation? "
        "Answer YES or NO.\n\n{chain}"
    ),
    "v51_constraint_adapted": (
        "[PLACEHOLDER: v5.1 constraint paragraph adapted for Pokémon domain — "
        "replace with approved text before running]\n\n"
        "Does the following Pokémon battle sequence contain a rule violation? "
        "Answer YES or NO.\n\n{chain}"
    ),
}

CONDITION_NAMES = list(PROMPTS.keys())


def run_experiment(
    chains: pd.DataFrame,
    models: list[str],
    budget: BudgetTracker,
    dry_run: bool = False,
) -> pd.DataFrame:
    rows = []
    total = len(chains) * len(models) * len(CONDITION_NAMES)
    done = 0

    for _, chain_row in chains.iterrows():
        chain_text = format_chain(chain_row["elements"])
        gt_label = "NO" if chain_row.get("chain_type") == "shuffled" else "YES"

        for model in models:
            for condition in CONDITION_NAMES:
                done += 1
                print(f"\r[D-1.4] {done}/{total} calls...", end="", flush=True)

                prompt = PROMPTS[condition].format(chain=chain_text)

                if dry_run:
                    response = "YES"
                    pt, ct, cost = 90, 30, 0.0003
                else:
                    response, pt, ct, cost = call_model(
                        model, prompt, budget, diagnostic="d_1_4"
                    )

                pred = parse_prediction(response)
                rows.append(dict(
                    chain_id=chain_row["chain_id"],
                    model=model,
                    condition=condition,
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


def compute_per_model_effects(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ctrl = results[results["condition"] == "control"]
    intv_cond = [c for c in CONDITION_NAMES if c != "control"][0]
    intv = results[results["condition"] == intv_cond]

    for model in MODELS:
        ctrl_m = ctrl[ctrl["model"] == model].set_index("chain_id")
        intv_m = intv[intv["model"] == model].set_index("chain_id")
        shared = ctrl_m.index.intersection(intv_m.index)
        if len(shared) < 10:
            continue

        stats = mcnemar_cell(
            ctrl_m.loc[list(shared), "correct"].values.astype(bool),
            intv_m.loc[list(shared), "correct"].values.astype(bool),
        )
        stats["model"] = model
        rows.append(stats)

    return pd.DataFrame(rows)


def compare_to_v1_baseline(effects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in effects.iterrows():
        model = row["model"]
        v1 = V1_ORIGINAL_EFFECTS.get(model, {})
        rows.append(dict(
            model=model,
            v1_accuracy_gap=v1.get("accuracy_gap"),
            v1_log_odds_approx=v1.get("log_odds_approx"),
            v51_method_log_odds=row["log_odds_effect"],
            v51_method_delta_acc=row["delta_acc"],
            retained_pct=(
                row["log_odds_effect"] / v1["log_odds_approx"] * 100
                if v1.get("log_odds_approx") else None
            ),
        ))
    return pd.DataFrame(rows)


def generate_summary(
    effects: pd.DataFrame,
    comparison: pd.DataFrame,
    output_path: Path,
):
    lines = [
        "# D-1.4 Factual Summary — v1 corpus replay",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        f"\nIntervention adaptation note: {INTERVENTION_ADAPTATION_NOTE}",
        "\n## v1 corpus effects under v5.1 methodology",
    ]

    for _, row in effects.iterrows():
        lines.append(
            f"- {row['model']}: log-odds effect={row['log_odds_effect']:.4f}, "
            f"Δacc={row['delta_acc']:.4f}, "
            f"p={row.get('p_value', float('nan')):.4f}"
        )

    lines += ["\n## Comparison to v1 original effects"]
    for _, row in comparison.iterrows():
        retained = f"{row['retained_pct']:.1f}%" if row["retained_pct"] is not None else "N/A"
        lines.append(
            f"- {row['model']}: "
            f"v1 gap={row['v1_accuracy_gap']}, "
            f"v5.1-method log-odds={row['v51_method_log_odds']:.4f}, "
            f"retained={retained}"
        )

    # Pre-reg decision rule check (§3.3.4)
    sonnet_effect = effects[effects["model"].str.contains("sonnet")]["log_odds_effect"]
    sonnet_eff = float(sonnet_effect.iloc[0]) if not sonnet_effect.empty else None

    lines += ["\n## Pre-reg decision rule check (pre-reg §3.3.4)"]
    if sonnet_eff is not None:
        if sonnet_eff >= 0.05 * 1.96:  # log-odds equivalent of Δacc≥0.05 at ~0.65 base
            lines.append("  → v1 corpus survives v5.1 methodology: "
                         "**null is corpus-specific**. Mew can train on v1-style corpora.")
        elif sonnet_eff < -0.05:
            lines.append("  → v1 shows reversal: "
                         "**v5.1 intervention is actively harmful on v1 corpus.**")
        else:
            lines.append("  → v1 corpus also nulls: **methodology change explains v5.1 null.**")
    else:
        lines.append("  → Sonnet effect not computed.")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="D-1.4: v1 corpus replay")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    budget = BudgetTracker()

    if args.test or args.dry_run:
        from tier1.d_1_1_symbolic_detection.d_1_1_runner import generate_synthetic_corpus
        corpus = generate_synthetic_corpus()
        corpus["domain"] = "pokemon"
    else:
        print(f"[D-1.4] Loading v1 corpus from {args.data_dir}")
        corpus = load_corpus(args.data_dir)

    print(f"[D-1.4] {len(corpus)} chains | Models: {MODELS}")
    print(f"[D-1.4] Adaptation note: {INTERVENTION_ADAPTATION_NOTE[:80]}...")
    print("[D-1.4] Verify PLACEHOLDER text in PROMPTS dict before live run.")

    results = run_experiment(corpus, MODELS, budget, dry_run=args.dry_run or args.test)
    results.to_csv(args.output_dir / "raw_responses.csv", index=False)

    effects = compute_per_model_effects(results)
    effects.to_csv(args.output_dir / "effects_per_model.csv", index=False)

    comparison = compare_to_v1_baseline(effects)
    comparison.to_csv(args.output_dir / "comparison_to_v1.csv", index=False)

    generate_summary(effects, comparison, args.output_dir / "summary.md")

    print(f"[D-1.4] Outputs written to {args.output_dir}")
    print(f"[D-1.4] Cumulative budget: ${budget.cumulative_cost():.2f}")


if __name__ == "__main__":
    main()
