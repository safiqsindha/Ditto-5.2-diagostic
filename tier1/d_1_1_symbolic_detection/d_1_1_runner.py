"""
D-1.1: Symbolic detection runner
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Runs domain-specific rule-checkers on the full v5 corpus and computes:
  - Per-domain symbolic detection accuracy (real vs shuffled)
  - Per-chain agreement matrix with LLM predictions (from v5.1 raw data)
  - Story A / B / A-narrow determination

Inputs:
    data/v5_corpus/
    data/v5.1_raw/   (for LLM prediction cross-reference)

Outputs per domain:
    tier1_outputs/d_1_1/{domain}_symbolic_results.csv
    tier1_outputs/d_1_1/{domain}_agreement_matrix.csv
    tier1_outputs/d_1_1/{domain}_summary.md
Cross-domain:
    tier1_outputs/d_1_1/d_1_1_overall_summary.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.data_loader import load_corpus, load_v51_raw
from tier1.d_1_1_symbolic_detection import DOMAIN_CHECKERS

DATA_CORPUS = Path("data/v5_corpus")
DATA_V51 = Path("data/v5.1_raw")
OUTPUT_DIR = Path("tier1_outputs/d_1_1")

# Pre-reg §3.3.1 decision thresholds
STORY_A_THRESHOLD = 0.90    # symbolic accuracy ≥ 90% on ≥3 domains → Story A
STORY_B_THRESHOLD = 0.60    # symbolic accuracy < 60% on most domains → Story B


def run_symbolic_detection(corpus: pd.DataFrame, domain: str) -> pd.DataFrame:
    """Apply symbolic rule-checker to all chains in a domain."""
    checker = DOMAIN_CHECKERS.get(domain)
    if checker is None:
        raise ValueError(f"No rule-checker for domain: {domain}")

    domain_df = corpus[corpus["domain"] == domain].copy()
    results = []

    for _, row in domain_df.iterrows():
        chain = row["elements"]
        if not isinstance(chain, list):
            continue
        result = checker(chain)
        results.append(dict(
            chain_id=row["chain_id"],
            domain=domain,
            chain_type=row["chain_type"],
            symbolic_violation=result.violation,
            violation_type=result.violation_type,
            violation_position=result.position,
            details=result.details,
        ))

    return pd.DataFrame(results)


def compute_accuracy(results: pd.DataFrame) -> dict:
    """
    Compute symbolic detection accuracy.

    In the Ditto framing: real chains should NOT have violations;
    shuffled chains SHOULD have violations (detectable structural break).
    Symbolic detection 'predicts' shuffled = violation present.
    """
    real = results[results["chain_type"] == "real"]
    shuffled = results[results["chain_type"] == "shuffled"]

    real_correct = int((real["symbolic_violation"] == False).sum())
    shuf_correct = int((shuffled["symbolic_violation"] == True).sum())
    total = len(results)
    correct = real_correct + shuf_correct

    return {
        "n_real": len(real),
        "n_shuffled": len(shuffled),
        "real_tn_rate": real_correct / max(len(real), 1),
        "shuffled_tp_rate": shuf_correct / max(len(shuffled), 1),
        "overall_accuracy": correct / max(total, 1),
    }


def compute_agreement_matrix(
    symbolic: pd.DataFrame,
    llm_df: pd.DataFrame | None,
    domain: str,
) -> pd.DataFrame:
    """
    Compute agreement between symbolic predictions and LLM predictions.
    If no LLM data provided, return symbolic-only DataFrame.
    """
    symbolic["symbolic_pred_shuffled"] = symbolic["symbolic_violation"].astype(bool)

    if llm_df is None or llm_df.empty:
        return symbolic

    llm_domain = llm_df[
        (llm_df["domain"] == domain) & (llm_df["condition"] == "control")
    ][["chain_id", "model", "predicted_label", "ground_truth_label", "correct"]]

    merged = symbolic.merge(llm_domain, on="chain_id", how="left")
    return merged


def write_domain_summary(
    domain: str,
    results: pd.DataFrame,
    accuracy: dict,
    output_path: Path,
):
    violation_types = results[results["symbolic_violation"]]["violation_type"].value_counts()

    lines = [
        f"# D-1.1: {domain.upper()} symbolic detection summary",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        f"\n## Accuracy metrics",
        f"- Total chains: {len(results)}",
        f"- Real chains (n={accuracy['n_real']}): "
        f"true-negative rate = {accuracy['real_tn_rate']:.3f}",
        f"- Shuffled chains (n={accuracy['n_shuffled']}): "
        f"true-positive rate (violation detected) = {accuracy['shuffled_tp_rate']:.3f}",
        f"- **Overall symbolic detection accuracy: {accuracy['overall_accuracy']:.3f}**",
        "\n## Violation types detected",
    ]
    for vtype, count in violation_types.items():
        lines.append(f"- {vtype}: {count}")

    if not violation_types.empty:
        pass
    else:
        lines.append("- (None)")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def write_overall_summary(
    domain_accuracies: dict[str, dict],
    output_path: Path,
):
    n_story_a = sum(
        1 for acc in domain_accuracies.values()
        if acc["overall_accuracy"] >= STORY_A_THRESHOLD
    )

    lines = [
        "# D-1.1: Overall symbolic detection summary",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        f"\n## Per-domain accuracy",
    ]
    for domain, acc in domain_accuracies.items():
        lines.append(
            f"- {domain}: accuracy={acc['overall_accuracy']:.3f} "
            f"(real TN={acc['real_tn_rate']:.3f}, shuffled TP={acc['shuffled_tp_rate']:.3f})"
        )

    lines += [
        f"\n## Story determination (pre-reg §3.3.1)",
        f"- Story A threshold: ≥{STORY_A_THRESHOLD} accuracy on ≥3 domains",
        f"- Story B threshold: <{STORY_B_THRESHOLD} accuracy on most domains",
        f"- Domains meeting Story A threshold: {n_story_a}",
    ]

    if n_story_a >= 3:
        story = "**STORY A** — Chains carry structural property. Mew bridge intact."
    elif all(acc["overall_accuracy"] < STORY_B_THRESHOLD
             for acc in domain_accuracies.values()):
        story = "**STORY B** — Chains do not carry property as conceived."
    else:
        story = "**STORY A-NARROW** — Mixed. Some domains admit detection; others do not."

    lines += [
        f"\n## Pre-registered outcome: {story}",
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def generate_synthetic_corpus() -> pd.DataFrame:
    """Synthetic corpus: shuffled chains deliberately embed PUBG health violations."""
    import numpy as np
    rng = np.random.default_rng(101)
    rows = []
    for domain in DOMAIN_CHECKERS:
        for chain_type in ["real", "shuffled"]:
            for cid in range(30):
                if domain == "pubg" and chain_type == "shuffled":
                    elements = [
                        {"player_1": {"health": 80, "armor": 50, "ammo": 30}},
                        {"player_1": {"health": 200, "armor": 50, "ammo": 30}},  # violation
                    ]
                elif domain == "poker" and chain_type == "shuffled":
                    elements = [
                        {"street": "preflop", "community_cards": ["AH", "KD", "AH"]},  # dup
                    ]
                else:
                    elements = [{"event": f"state_{i}"} for i in range(5)]
                rows.append(dict(
                    chain_id=f"{domain}_{chain_type}_{cid:04d}",
                    domain=domain,
                    chain_type=chain_type,
                    elements=elements,
                ))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="D-1.1: Symbolic detection runner")
    parser.add_argument("--corpus-dir", type=Path, default=DATA_CORPUS)
    parser.add_argument("--v51-dir", type=Path, default=DATA_V51)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="No-op for D-1.1 (no API calls); treated as --test")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.test or args.dry_run:
        print("[D-1.1] Running on synthetic corpus.")
        corpus = generate_synthetic_corpus()
        llm_df = None
    else:
        print(f"[D-1.1] Loading v5 corpus from {args.corpus_dir}")
        corpus = load_corpus(args.corpus_dir)
        try:
            llm_df = load_v51_raw(args.v51_dir)
        except FileNotFoundError:
            print("[D-1.1] v5.1 raw data not found; skipping LLM agreement matrix.")
            llm_df = None

    domain_accuracies = {}

    for domain in DOMAIN_CHECKERS:
        if domain not in corpus["domain"].values:
            print(f"[D-1.1] Domain '{domain}' not in corpus — skipping.")
            continue

        print(f"[D-1.1] Processing domain: {domain}")
        symbolic_results = run_symbolic_detection(corpus, domain)
        accuracy = compute_accuracy(symbolic_results)
        agreement = compute_agreement_matrix(symbolic_results, llm_df, domain)

        symbolic_results.to_csv(args.output_dir / f"{domain}_symbolic_results.csv", index=False)
        agreement.to_csv(args.output_dir / f"{domain}_agreement_matrix.csv", index=False)
        write_domain_summary(domain, symbolic_results, accuracy,
                             args.output_dir / f"{domain}_summary.md")

        domain_accuracies[domain] = accuracy
        print(f"[D-1.1] {domain}: accuracy={accuracy['overall_accuracy']:.3f}")

    write_overall_summary(domain_accuracies, args.output_dir / "d_1_1_overall_summary.md")
    print(f"\n[D-1.1] Outputs written to {args.output_dir}")


if __name__ == "__main__":
    main()
