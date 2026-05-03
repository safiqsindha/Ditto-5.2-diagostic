"""
D-0.2: Confusion-matrix structure on anti-detecting models
Pre-reg reference: DDK_v0.1_PREREG.md §3.1.2

Question: What is structurally happening when GPT-5, GPT-5.4-mini, and
Gemini 3 Flash Preview anti-detect?

Inputs:  data/v5.1_raw/
Outputs: tier0_outputs/d_0_2/mechanism_breakdown.csv
         tier0_outputs/d_0_2/representative_responses.md
         tier0_outputs/d_0_2/summary.md
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_v51_raw

DATA_DIR = Path("data/v5.1_raw")
OUTPUT_DIR = Path("tier0_outputs/d_0_2")

ANTI_DETECTING_MODELS = ["gpt-5", "gpt-5.4-mini", "gemini-3-flash-preview"]
PRO_DETECTING_MODEL = "glm-5"

# Regex patterns for mechanism classification (pre-reg §3.1.2)
# Precision/recall validated manually on ≥20 responses before running.
ACTIVE_FLIP_PATTERNS = [
    r"\bno\b",
    r"\bnot a violation\b",
    r"\bvalid\b",
    r"\bdoes not violate\b",
    r"\bfollows the rules\b",
    r"\bno violation\b",
]

ABSTENTION_PATTERNS = [
    r"\buncertain\b",
    r"\bunclear\b",
    r"\bhard to say\b",
    r"\bcannot determine\b",
    r"\bdifficult to assess\b",
    r"\bmight\b",
    r"\bpossibly\b",
    r"\bperhaps\b",
    r"\bi('m| am) not sure\b",
    r"\bcould go either way\b",
]

BREAKDOWN_PATTERNS = [
    r"\bi('m| am) (unable|not able) to\b",
    r"\bi cannot\b",
    r"\bi refuse\b",
    r"\bapologies\b",
    r"\bi don'?t (have access|know enough)\b",
    r"^[^a-zA-Z]*$",  # response with no alphabetical content
]


def classify_response(response: str) -> str:
    """
    Classify a response into: active_flip, abstention, output_breakdown, or unclear.

    Pre-reg §3.1.2: use string-matching rules + optional LLM cross-check.
    This function implements the string-matching primary classifier.
    """
    text = response.lower().strip()

    breakdown_count = sum(
        1 for p in BREAKDOWN_PATTERNS if re.search(p, text, re.IGNORECASE)
    )
    abstention_count = sum(
        1 for p in ABSTENTION_PATTERNS if re.search(p, text, re.IGNORECASE)
    )
    flip_count = sum(
        1 for p in ACTIVE_FLIP_PATTERNS if re.search(p, text, re.IGNORECASE)
    )

    if breakdown_count >= 2:
        return "output_breakdown"
    if abstention_count > flip_count and abstention_count >= 2:
        return "abstention"
    if flip_count >= 1:
        return "active_flip"
    return "unclear"


def extract_anti_detecting_cases(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to anti-detection events: control=correct AND intervention=wrong.
    Applied to anti-detecting models only.
    """
    anti_df = df[df["model"].isin(ANTI_DETECTING_MODELS)].copy()

    ctrl = anti_df[anti_df["condition"] == "control"].set_index(["chain_id", "model"])
    intv = anti_df[anti_df["condition"] == "intervention"].set_index(["chain_id", "model"])

    shared = ctrl.index.intersection(intv.index)
    ctrl_s = ctrl.loc[shared]
    intv_s = intv.loc[shared]

    anti_detect_mask = ctrl_s["correct"] & ~intv_s["correct"]
    anti_chains = anti_detect_mask[anti_detect_mask].index

    cases = intv.loc[anti_chains].reset_index()
    ctrl_resp = ctrl.loc[anti_chains, ["response", "ground_truth_label"]].reset_index()
    ctrl_resp = ctrl_resp.rename(columns={"response": "ctrl_response"})

    merged = cases.merge(ctrl_resp, on=["chain_id", "model"])
    return merged


def compute_mechanism_breakdown(cases: pd.DataFrame) -> pd.DataFrame:
    cases = cases.copy()
    cases["mechanism"] = cases["response"].apply(classify_response)
    return cases


def mechanism_shares(cases: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, grp in cases.groupby("model"):
        total = len(grp)
        for mech in ["active_flip", "abstention", "output_breakdown", "unclear"]:
            count = int((grp["mechanism"] == mech).sum())
            rows.append(dict(
                model=model,
                mechanism=mech,
                count=count,
                share=count / total if total > 0 else 0.0,
            ))
    return pd.DataFrame(rows)


def write_representative_responses(cases: pd.DataFrame, output_path: Path, n_per: int = 5):
    lines = [
        "# D-0.2: Representative anti-detection responses by mechanism",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n_These are raw model outputs. No interpretation._\n",
    ]
    for model in ANTI_DETECTING_MODELS:
        m_cases = cases[cases["model"] == model]
        for mech in ["active_flip", "abstention", "output_breakdown", "unclear"]:
            sample = m_cases[m_cases["mechanism"] == mech].head(n_per)
            if sample.empty:
                continue
            lines.append(f"\n## {model} — {mech} (n={len(sample)} shown, "
                         f"total={(m_cases['mechanism'] == mech).sum()})")
            for _, row in sample.iterrows():
                lines.append(f"\n**chain_id:** {row['chain_id']}")
                lines.append(f"**Control response:** {row.get('ctrl_response', 'N/A')[:200]}")
                lines.append(f"**Intervention response:** {str(row['response'])[:400]}")
                lines.append("---")
    output_path.write_text("\n".join(lines))


def generate_summary(shares: pd.DataFrame, output_path: Path):
    lines = [
        "# D-0.2 Factual Summary — Confusion-matrix structure",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
    ]
    for model in ANTI_DETECTING_MODELS:
        m = shares[shares["model"] == model]
        total = m["count"].sum()
        if total == 0:
            continue
        lines.append(f"\n## {model} ({total} anti-detection cases)")
        for _, row in m.iterrows():
            lines.append(f"- {row['mechanism']}: {row['count']} ({row['share']*100:.1f}%)")

        dom_mech = "active_flip" if (
            m[m["mechanism"] == "active_flip"]["share"].values[0] > 0.6
        ) else "abstention" if (
            m[m["mechanism"] == "abstention"]["share"].values[0] > 0.6
        ) else "mixed"
        lines.append(f"  → Dominant mechanism: **{dom_mech}**")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def generate_synthetic_test_data() -> pd.DataFrame:
    """50 anti-detection events per model with known mechanism distribution."""
    import numpy as np
    rng = np.random.default_rng(99)
    rows = []
    templates = {
        "active_flip": [
            "No, this is not a violation. The sequence follows the rules correctly.",
            "This appears valid and does not violate any constraints.",
        ],
        "abstention": [
            "I'm not sure whether this constitutes a violation. Perhaps it might, but it's unclear.",
            "It's hard to say. This could possibly be a violation, but I cannot determine with certainty.",
        ],
        "output_breakdown": [
            "I am unable to assist with this request.",
            "I cannot assess this.",
        ],
    }
    mechs = list(templates.keys())
    for model in ANTI_DETECTING_MODELS:
        for i in range(50):
            gt = "YES"
            mech = rng.choice(mechs)
            response = rng.choice(templates[mech])
            rows.append(dict(
                chain_id=f"synthetic_{i:04d}",
                model=model,
                domain="pubg",
                condition="intervention",
                response=response,
                ctrl_response="YES, this is clearly a violation.",
                predicted_label="NO",
                ground_truth_label=gt,
                correct=False,
            ))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="D-0.2: Confusion-matrix structure")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.test:
        print("[D-0.2] Running on synthetic test data.")
        cases = generate_synthetic_test_data()
    else:
        print(f"[D-0.2] Loading data from {args.data_dir}")
        df = load_v51_raw(args.data_dir)
        cases = extract_anti_detecting_cases(df)

    print(f"[D-0.2] {len(cases)} anti-detection cases found across "
          f"{cases['model'].nunique()} models")

    cases = compute_mechanism_breakdown(cases)
    shares = mechanism_shares(cases)

    cases.to_csv(args.output_dir / "mechanism_breakdown.csv", index=False)
    shares.to_csv(args.output_dir / "mechanism_shares.csv", index=False)
    write_representative_responses(cases, args.output_dir / "representative_responses.md")
    generate_summary(shares, args.output_dir / "summary.md")

    print(f"[D-0.2] Outputs written to {args.output_dir}")


if __name__ == "__main__":
    main()
