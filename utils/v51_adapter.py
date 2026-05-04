"""
Convert v5.1 tidy_long.csv to the format expected by load_v51_raw().

Usage:
    python utils/v51_adapter.py \
        --input ~/Desktop/Project\ Ditto/Ditto\ V5.1\ Final/03_analysis_outputs/phase3_consolidated/tidy_long.csv \
        --output data/v5.1_raw/v51_raw.csv

Output columns: chain_id, model, domain, condition, response,
                predicted_label, ground_truth_label, correct
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def convert(input_path: Path, output_path: Path) -> None:
    print(f"[adapter] Reading {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    print(f"[adapter] {len(df):,} rows, columns: {list(df.columns)}")

    # Filter to marker=1, strict=1 → one row per (model, chain_id, condition)
    # This is the "marker+strict" sub-condition used throughout the primary analysis
    sub = df[(df["marker"] == 1) & (df["strict"] == 1)].copy()
    print(f"[adapter] After marker=1, strict=1 filter: {len(sub):,} rows")

    # Map columns
    sub["model"] = sub["model_id"]
    sub["domain"] = sub["cell"]
    sub["condition"] = sub["intervention"].map({0: "control", 1: "intervention"})

    # parsed_strict: yes/no/NaN → predicted_label YES/NO/ABSTAIN
    sub["predicted_label"] = (
        sub["parsed_strict"].str.upper().where(sub["parsed_strict"].notna(), other="ABSTAIN")
    )
    sub["response"] = sub["predicted_label"]

    # ground truth: clean→YES (consistent), adversarial→NO (violation present)
    sub["ground_truth_label"] = sub["chain_class"].map({"clean": "YES", "adversarial": "NO"})

    # correct: predicted matches ground truth (ABSTAIN always wrong)
    sub["correct"] = sub["predicted_label"] == sub["ground_truth_label"]

    out_cols = [
        "chain_id", "model", "domain", "condition",
        "response", "predicted_label", "ground_truth_label", "correct",
    ]
    result = sub[out_cols].reset_index(drop=True)

    # Sanity check
    n_models = result["model"].nunique()
    n_domains = result["domain"].nunique()
    n_chains = result.groupby(["model", "domain", "condition"])["chain_id"].nunique().mean()
    print(f"[adapter] {n_models} models, {n_domains} domains, ~{n_chains:.0f} chains/cell")
    print(f"[adapter] Overall accuracy: {result['correct'].mean():.3f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"[adapter] Written {len(result):,} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert v5.1 tidy_long.csv to DDK format")
    parser.add_argument("--input", type=Path, required=True, help="Path to tidy_long.csv")
    parser.add_argument("--output", type=Path, default=Path("data/v5.1_raw/v51_raw.csv"))
    args = parser.parse_args()
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
