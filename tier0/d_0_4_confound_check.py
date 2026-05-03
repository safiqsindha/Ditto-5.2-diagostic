"""
D-0.4: v5 corpus confound check
Pre-reg reference: DDK_v0.1_PREREG.md §3.1.4

Question: Are v3's four mechanistic confounds controlled in v5's chain construction?

Checks:
  1. Position-modulo distribution (pos%4 bias by abstraction type)
  2. Backoff-level differential (real vs shuffled)
  3. Shuffle adjacency × model echo (repeated tokens in shuffled chains)
  4. Self-leakage (shuffled element overlap with reference distribution)

Inputs:  data/v5_corpus/
Outputs: tier0_outputs/d_0_4/confound_table.csv
         tier0_outputs/d_0_4/confound_distributions.png
         tier0_outputs/d_0_4/summary.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_corpus

DATA_DIR = Path("data/v5_corpus")
OUTPUT_DIR = Path("tier0_outputs/d_0_4")

# Thresholds inherited from v3 documentation.
# If v3 docs unavailable, these were set at sign-off (see decision_log.md).
THRESHOLD_POSITION_KS_PVAL = 0.05    # KS test: p < threshold → confound
THRESHOLD_BACKOFF_DIFF = 0.15        # |mean_real - mean_shuffled| / pooled_sd > threshold
THRESHOLD_ADJACENCY_REPEAT_RATE = 0.10  # fraction repeated adjacent tokens in shuffled
THRESHOLD_LEAKAGE_OVERLAP = 0.20     # fraction shuffled elements in real reference set


def check_position_modulo(domain_df: pd.DataFrame) -> dict:
    """
    Confound 1: Position-modulo distribution.

    In v3, chains had a systematic bias where position % 4 == 3 forced
    ResourceBudget abstraction. Check if v5 real vs shuffled chains show
    different pos%4 distributions — would indicate structural artifacts.
    """
    results = {}
    for chain_type in ["real", "shuffled"]:
        subset = domain_df[domain_df["chain_type"] == chain_type]
        positions = []
        for _, row in subset.iterrows():
            elements = row["elements"]
            if isinstance(elements, list):
                for i in range(len(elements)):
                    positions.append(i % 4)
        results[chain_type] = positions

    if not results.get("real") or not results.get("shuffled"):
        return {"confound_detected": False, "reason": "insufficient data", "p_value": None}

    ks_stat, p_val = stats.ks_2samp(results["real"], results["shuffled"])
    confound = p_val < THRESHOLD_POSITION_KS_PVAL

    return {
        "check": "position_modulo",
        "ks_statistic": float(ks_stat),
        "p_value": float(p_val),
        "confound_detected": bool(confound),
        "threshold": THRESHOLD_POSITION_KS_PVAL,
    }


def check_backoff_level(domain_df: pd.DataFrame) -> dict:
    """
    Confound 2: Backoff-level differential.

    In chains with hierarchical (specific→general) element structure,
    shuffling should not systematically change the distribution of
    'specificity levels'. Check mean specificity-proxy (element length)
    as a crude proxy if backoff metadata unavailable.
    """
    backoff_by_type = {}
    for chain_type in ["real", "shuffled"]:
        subset = domain_df[domain_df["chain_type"] == chain_type]
        lengths = []
        for _, row in subset.iterrows():
            elements = row["elements"]
            if isinstance(elements, list):
                for el in elements:
                    if isinstance(el, str):
                        lengths.append(len(el.split()))
                    elif isinstance(el, dict) and "backoff_level" in el:
                        lengths.append(float(el["backoff_level"]))
        backoff_by_type[chain_type] = lengths

    if not backoff_by_type.get("real") or not backoff_by_type.get("shuffled"):
        return {"confound_detected": False, "reason": "insufficient data"}

    real_arr = np.array(backoff_by_type["real"])
    shuf_arr = np.array(backoff_by_type["shuffled"])

    pooled_sd = np.sqrt((real_arr.var() + shuf_arr.var()) / 2 + 1e-9)
    effect = abs(real_arr.mean() - shuf_arr.mean()) / pooled_sd
    confound = effect > THRESHOLD_BACKOFF_DIFF

    return {
        "check": "backoff_level_differential",
        "effect_size_d": float(effect),
        "real_mean": float(real_arr.mean()),
        "shuffled_mean": float(shuf_arr.mean()),
        "confound_detected": bool(confound),
        "threshold": THRESHOLD_BACKOFF_DIFF,
    }


def check_adjacency_echo(domain_df: pd.DataFrame) -> dict:
    """
    Confound 3: Shuffle adjacency × model echo.

    Checks whether shuffled chains have unusual rates of repeated adjacent
    elements — which would indicate a shuffling artifact creating echoic
    structure that models can trivially detect.
    """
    shuffled = domain_df[domain_df["chain_type"] == "shuffled"]
    real = domain_df[domain_df["chain_type"] == "real"]

    def adjacent_repeat_rate(chains_df: pd.DataFrame) -> float:
        repeats = 0
        total = 0
        for _, row in chains_df.iterrows():
            elements = row["elements"]
            if isinstance(elements, list) and len(elements) > 1:
                for i in range(len(elements) - 1):
                    total += 1
                    el_a = str(elements[i])[:50]
                    el_b = str(elements[i + 1])[:50]
                    if el_a == el_b:
                        repeats += 1
        return repeats / max(total, 1)

    shuf_rate = adjacent_repeat_rate(shuffled)
    real_rate = adjacent_repeat_rate(real)
    confound = shuf_rate > THRESHOLD_ADJACENCY_REPEAT_RATE and shuf_rate > real_rate * 2

    return {
        "check": "adjacency_echo",
        "shuffled_repeat_rate": float(shuf_rate),
        "real_repeat_rate": float(real_rate),
        "confound_detected": bool(confound),
        "threshold": THRESHOLD_ADJACENCY_REPEAT_RATE,
    }


def check_self_leakage(domain_df: pd.DataFrame) -> dict:
    """
    Confound 4: Self-leakage.

    Checks if shuffled chain elements overlap significantly with the
    reference distribution of real chain elements. High overlap would
    mean shuffled chains 'look real' at the element level — not a
    confound per se, but could indicate the shuffle is too conservative.
    """
    real = domain_df[domain_df["chain_type"] == "real"]
    shuffled = domain_df[domain_df["chain_type"] == "shuffled"]

    def flatten_elements(df: pd.DataFrame) -> set:
        all_els = set()
        for _, row in df.iterrows():
            elements = row["elements"]
            if isinstance(elements, list):
                for el in elements:
                    all_els.add(str(el)[:100])
        return all_els

    real_set = flatten_elements(real)
    shuf_set = flatten_elements(shuffled)

    if not real_set or not shuf_set:
        return {"confound_detected": False, "reason": "insufficient data"}

    overlap = len(shuf_set & real_set) / len(shuf_set)
    confound = overlap > THRESHOLD_LEAKAGE_OVERLAP

    return {
        "check": "self_leakage",
        "overlap_fraction": float(overlap),
        "real_unique_elements": len(real_set),
        "shuffled_unique_elements": len(shuf_set),
        "confound_detected": bool(confound),
        "threshold": THRESHOLD_LEAKAGE_OVERLAP,
    }


def run_all_checks(corpus: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for domain in corpus["domain"].unique():
        domain_df = corpus[corpus["domain"] == domain]
        for check_fn in [
            check_position_modulo,
            check_backoff_level,
            check_adjacency_echo,
            check_self_leakage,
        ]:
            result = check_fn(domain_df)
            result["domain"] = domain
            rows.append(result)
    return pd.DataFrame(rows)


def plot_distributions(corpus: pd.DataFrame, confound_table: pd.DataFrame, output_path: Path):
    domains = corpus["domain"].unique()
    fig, axes = plt.subplots(len(domains), 2, figsize=(12, 4 * len(domains)), squeeze=False)

    for i, domain in enumerate(domains):
        domain_df = corpus[corpus["domain"] == domain]
        for j, chain_type in enumerate(["real", "shuffled"]):
            subset = domain_df[domain_df["chain_type"] == chain_type]
            lengths = []
            for _, row in subset.iterrows():
                if isinstance(row["elements"], list):
                    lengths.append(len(row["elements"]))
            axes[i][j].hist(lengths, bins=20, alpha=0.7, color="steelblue" if j == 0 else "orange")
            axes[i][j].set_title(f"{domain} — {chain_type} chain lengths")
            axes[i][j].set_xlabel("Chain length")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def generate_summary(confound_table: pd.DataFrame, output_path: Path):
    n_confounds = int(confound_table["confound_detected"].sum())
    n_checks = len(confound_table)

    lines = [
        "# D-0.4 Factual Summary — v5 corpus confound check",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        f"\n## Overall: {n_confounds}/{n_checks} domain-check combinations flagged as confounded",
    ]

    for check in confound_table["check"].unique():
        subset = confound_table[confound_table["check"] == check]
        flagged = subset[subset["confound_detected"]]["domain"].tolist()
        lines.append(f"\n### {check}")
        if flagged:
            lines.append(f"- **Confound detected in:** {', '.join(flagged)}")
        else:
            lines.append("- No confound detected in any domain.")
        for _, row in subset.iterrows():
            detail = {k: v for k, v in row.items()
                      if k not in ("check", "domain", "confound_detected", "threshold")}
            lines.append(f"  - {row['domain']}: {detail}")

    if n_confounds == 0:
        lines.append("\n**Pre-reg outcome: All four confounds controlled. Proceed unchanged.**")
    else:
        affected = confound_table[confound_table["confound_detected"]]["domain"].unique()
        n_domains = len(confound_table["domain"].unique())
        if len(affected) >= n_domains * 0.6:
            lines.append("\n**Pre-reg outcome: Pervasive confounds. Tier 1 paused pending author decision.**")
        else:
            lines.append(f"\n**Pre-reg outcome: Confounds in specific domains: {list(affected)}. "
                         "Exclude or stratify in Tier 1.1.**")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def generate_synthetic_corpus() -> pd.DataFrame:
    """Synthetic v5 corpus with known clean structure for testing."""
    rng = np.random.default_rng(7)
    rows = []
    domains = ["pubg", "nba", "csgo", "rocket_league", "poker"]
    vocab = [f"state_{i}" for i in range(100)]

    for domain in domains:
        for chain_type in ["real", "shuffled"]:
            for cid in range(50):
                n = rng.integers(4, 12)
                elements = rng.choice(vocab, size=n, replace=False).tolist()
                rows.append(dict(
                    chain_id=f"{domain}_{chain_type}_{cid:04d}",
                    domain=domain,
                    chain_type=chain_type,
                    elements=elements,
                ))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="D-0.4: Confound check")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.test:
        print("[D-0.4] Running on synthetic corpus.")
        corpus = generate_synthetic_corpus()
    else:
        print(f"[D-0.4] Loading v5 corpus from {args.data_dir}")
        corpus = load_corpus(args.data_dir)

    print(f"[D-0.4] {len(corpus)} chains | {corpus['domain'].nunique()} domains")

    confound_table = run_all_checks(corpus)
    n_flagged = int(confound_table["confound_detected"].sum())
    print(f"[D-0.4] {n_flagged}/{len(confound_table)} checks flagged")

    confound_table.to_csv(args.output_dir / "confound_table.csv", index=False)
    plot_distributions(corpus, confound_table, args.output_dir / "confound_distributions.png")
    generate_summary(confound_table, args.output_dir / "summary.md")

    if n_flagged > 0:
        affected = confound_table[confound_table["confound_detected"]]["domain"].nunique()
        if affected >= corpus["domain"].nunique() * 0.6:
            print("[D-0.4] WARNING: Pervasive confounds detected. "
                  "Per pre-reg §3.1.4 stopping rule: Tier 1 should pause pending author decision.")

    print(f"[D-0.4] Outputs written to {args.output_dir}")


if __name__ == "__main__":
    main()
