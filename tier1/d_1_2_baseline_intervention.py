"""
D-1.2: Baseline-intervention comparison
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.2

Question: Does the v5.1 panel respond to ANY prompt-level intervention,
or is it the specific constraint paragraph that fails?

5 models × 200 chains × 4 conditions = 4,000 calls (~$30-50)
Hard cap: $80

Conditions:
  1. control         — no intervention
  2. v51_constraint  — exact v5.1 constraint paragraph
  3. three_shot      — 3-shot exemplars with rule violation explanations
  4. cot             — "think step by step before answering"

Outputs: tier1_outputs/d_1_2/effects_per_intervention.csv
         tier1_outputs/d_1_2/effects_plot.png
         tier1_outputs/d_1_2/raw_responses.csv
         tier1_outputs/d_1_2/summary.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.budget import BudgetTracker
from utils.data_loader import load_corpus
from utils.scoring import bh_fdr_correct, mcnemar_cell

DATA_DIR = Path("data/v5_corpus")
OUTPUT_DIR = Path("tier1_outputs/d_1_2")

# Default model panel per pre-reg §3.3.2
DEFAULT_MODELS = [
    "gpt-5",
    "claude-sonnet-4-5",
    "qwen3.6-plus",
    "glm-5",
    "claude-haiku-4-5",
]

N_CHAINS = 200
RANDOM_SEED = 2026  # same seed as v5.1 for reproducibility

CONDITION_NAMES = ["control", "v51_constraint", "three_shot", "cot"]

# Intervention prompt templates — content held constant across D-1.3 format variants.
# These must be reviewed and approved before running.
PROMPTS = {
    "control": (
        "Does the following sequence contain a rule violation? "
        "Answer YES or NO.\n\n{chain}"
    ),
    "v51_constraint": (
        # PLACEHOLDER: Insert exact v5.1 constraint paragraph here.
        # DO NOT modify this until authors approve the exact wording.
        "[PLACEHOLDER: v5.1 constraint paragraph — fill in before running]\n\n"
        "Does the following sequence contain a rule violation? "
        "Answer YES or NO.\n\n{chain}"
    ),
    "three_shot": (
        "Here are three examples of rule violations:\n\n"
        "Example 1: [PLACEHOLDER: example 1 with explanation]\n"
        "Answer: YES — because [reason]\n\n"
        "Example 2: [PLACEHOLDER: example 2 with explanation]\n"
        "Answer: YES — because [reason]\n\n"
        "Example 3: [PLACEHOLDER: example 3 with explanation]\n"
        "Answer: YES — because [reason]\n\n"
        "Now answer: Does the following sequence contain a rule violation? "
        "Answer YES or NO.\n\n{chain}"
    ),
    "cot": (
        "Think step by step before answering. "
        "Does the following sequence contain a rule violation? "
        "Answer YES or NO.\n\n{chain}"
    ),
}


def sample_chains(corpus: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Sample n chains balanced across domains (n//n_domains per domain)."""
    rng = np.random.default_rng(seed)
    domains = corpus["domain"].unique()
    per_domain = max(1, n // len(domains))
    frames = []
    for domain in domains:
        domain_df = corpus[corpus["domain"] == domain]
        sample_n = min(per_domain, len(domain_df))
        idx = rng.choice(len(domain_df), size=sample_n, replace=False)
        frames.append(domain_df.iloc[idx])
    return pd.concat(frames, ignore_index=True).head(n)


def format_chain(chain_elements: list) -> str:
    """Serialize chain elements to a string for inclusion in prompts."""
    if isinstance(chain_elements, list):
        return "\n".join(str(el) for el in chain_elements)
    return str(chain_elements)


def call_model(
    model: str,
    prompt: str,
    budget: BudgetTracker,
    diagnostic: str = "d_1_2",
    max_retries: int = 5,
) -> tuple[str, int, int, float]:
    """
    Call a model API and return (response_text, prompt_tokens, completion_tokens, cost).

    Implements exponential backoff per build plan §5.1.
    """
    # Dispatch to appropriate client based on model name prefix
    if model.startswith("gpt") or model.startswith("o"):
        return _call_openai(model, prompt, budget, diagnostic, max_retries)
    elif model.startswith("claude") or model.startswith("haiku") or model.startswith("sonnet"):
        return _call_anthropic(model, prompt, budget, diagnostic, max_retries)
    elif model.startswith("gemini"):
        return _call_google(model, prompt, budget, diagnostic, max_retries)
    elif model.startswith("glm"):
        return _call_zhipu(model, prompt, budget, diagnostic, max_retries)
    elif model.startswith("qwen"):
        return _call_qwen(model, prompt, budget, diagnostic, max_retries)
    else:
        raise ValueError(f"Unknown model prefix: {model}")


def _call_anthropic(model, prompt, budget, diagnostic, max_retries):
    import anthropic
    # Map friendly names to API model IDs
    model_id_map = {
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-haiku-4-5": "claude-haiku-4-5-20251001",
        "haiku-4-5": "claude-haiku-4-5-20251001",
        "sonnet-4-5": "claude-sonnet-4-5",
    }
    model_id = model_id_map.get(model, model)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    for attempt in range(max_retries):
        try:
            resp = client.messages.create(
                model=model_id,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            pt = resp.usage.input_tokens
            ct = resp.usage.output_tokens
            # Approximate cost (update per current Anthropic pricing)
            cost = (pt * 3e-6) + (ct * 15e-6)
            budget.log(diagnostic, model, pt, ct, cost)
            return text, pt, ct, cost
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  Retry {attempt+1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def _call_openai(model, prompt, budget, diagnostic, max_retries):
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
            )
            text = resp.choices[0].message.content
            pt = resp.usage.prompt_tokens
            ct = resp.usage.completion_tokens
            cost = (pt * 2.5e-6) + (ct * 10e-6)  # approximate gpt-5 pricing
            budget.log(diagnostic, model, pt, ct, cost)
            return text, pt, ct, cost
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def _call_google(model, prompt, budget, diagnostic, max_retries):
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    client = genai.GenerativeModel(model)
    for attempt in range(max_retries):
        try:
            resp = client.generate_content(prompt)
            text = resp.text
            pt = resp.usage_metadata.prompt_token_count
            ct = resp.usage_metadata.candidates_token_count
            cost = (pt + ct) * 0.35e-6
            budget.log(diagnostic, model, pt, ct, cost)
            return text, pt, ct, cost
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def _call_zhipu(model, prompt, budget, diagnostic, max_retries):
    import requests
    api_key = os.environ["ZHIPU_API_KEY"]
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 256},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            pt = data["usage"]["prompt_tokens"]
            ct = data["usage"]["completion_tokens"]
            cost = (pt + ct) * 1e-6
            budget.log(diagnostic, model, pt, ct, cost)
            return text, pt, ct, cost
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def _call_qwen(model, prompt, budget, diagnostic, max_retries):
    import openai
    client = openai.OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
            )
            text = resp.choices[0].message.content
            pt = resp.usage.prompt_tokens
            ct = resp.usage.completion_tokens
            cost = (pt + ct) * 1e-6
            budget.log(diagnostic, model, pt, ct, cost)
            return text, pt, ct, cost
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def parse_prediction(response: str) -> str:
    """Extract YES/NO prediction from response text."""
    text = response.strip().upper()
    if text.startswith("YES"):
        return "YES"
    if text.startswith("NO"):
        return "NO"
    # Search for YES/NO anywhere in first 50 chars
    first = text[:50]
    if "YES" in first:
        return "YES"
    if "NO" in first:
        return "NO"
    return "UNCLEAR"


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
        gt = chain_row.get("ground_truth_label", chain_row.get("chain_type", ""))
        # Normalize: real=YES (is a valid chain), shuffled=NO (contains violation)
        # Adjust this mapping to match v5.1 labeling convention
        gt_label = "NO" if chain_row.get("chain_type") == "shuffled" else "YES"

        for model in models:
            for condition in CONDITION_NAMES:
                done += 1
                print(f"\r[D-1.2] {done}/{total} calls...", end="", flush=True)

                prompt = PROMPTS[condition].format(chain=chain_text)

                if dry_run:
                    response = "YES"
                    pt, ct, cost = 100, 50, 0.001
                else:
                    response, pt, ct, cost = call_model(model, prompt, budget)

                pred = parse_prediction(response)
                rows.append(dict(
                    chain_id=chain_row["chain_id"],
                    domain=chain_row.get("domain", ""),
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

    print()  # newline after progress
    return pd.DataFrame(rows)


def compute_intervention_effects(results: pd.DataFrame) -> pd.DataFrame:
    """Per (model, intervention_condition) effect vs control."""
    rows = []
    ctrl = results[results["condition"] == "control"]

    for model in results["model"].unique():
        for condition in CONDITION_NAMES:
            if condition == "control":
                continue
            intv = results[(results["model"] == model) & (results["condition"] == condition)]
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
            stats["condition"] = condition
            rows.append(stats)

    effects = pd.DataFrame(rows)
    if not effects.empty:
        _, p_adj = bh_fdr_correct(effects["p_value"].values)
        effects["p_value_adj_bh"] = p_adj
    return effects


def generate_summary(effects: pd.DataFrame, output_path: Path):
    lines = [
        "# D-1.2 Factual Summary — Baseline-intervention comparison",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n## Per (model, intervention) effects",
    ]
    for _, row in effects.iterrows():
        sig = "**" if row.get("p_value_adj_bh", 1) < 0.05 else ""
        lines.append(
            f"- {row['model']} × {row['condition']}: "
            f"log-odds={row['log_odds_effect']:.4f}, "
            f"p={row.get('p_value', float('nan')):.4f}, "
            f"p_adj={row.get('p_value_adj_bh', float('nan')):.4f} {sig}"
        )

    any_lift = effects[
        (effects["log_odds_effect"] >= 0.10) &
        (effects.get("p_value_adj_bh", pd.Series(1.0, index=effects.index)) < 0.05)
    ]
    lines += [
        "\n## Pre-reg decision rule check (pre-reg §3.3.2)",
        f"- Conditions with ≥0.10 log-odds lift and FDR significant: {len(any_lift)}",
    ]
    if len(any_lift) >= 1:
        lines.append("  → Panel responds to SOME intervention. "
                     "See synthesis for framing implications.")
    else:
        lines.append("  → No intervention class lifts performance at pre-reg threshold.")

    lines += [
        "\n---",
        "_Auto-generated factual summary. Interpretation deferred to authors._",
    ]
    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="D-1.2: Baseline-intervention comparison")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--n-chains", type=int, default=N_CHAINS)
    parser.add_argument("--dry-run", action="store_true", help="No API calls; use placeholder responses")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    budget = BudgetTracker()
    budget.check_alert()  # Verify not already over cap

    print(f"[D-1.2] Loading corpus from {args.data_dir}")
    if args.test or args.dry_run:
        from tier1.d_1_1_symbolic_detection.d_1_1_runner import generate_synthetic_corpus
        corpus = generate_synthetic_corpus()
    else:
        corpus = load_corpus(args.data_dir)

    chains = sample_chains(corpus, args.n_chains, RANDOM_SEED)
    print(f"[D-1.2] Selected {len(chains)} chains across {chains['domain'].nunique()} domains")
    print(f"[D-1.2] Models: {args.models}")
    print(f"[D-1.2] Total planned calls: {len(chains) * len(args.models) * len(CONDITION_NAMES)}")
    if not args.dry_run:
        print("[D-1.2] NOTE: Check that prompt templates are approved before running live.")
        print("        Verify PLACEHOLDER text in PROMPTS dict is replaced.")

    results = run_experiment(chains, args.models, budget, dry_run=args.dry_run or args.test)
    results.to_csv(args.output_dir / "raw_responses.csv", index=False)

    effects = compute_intervention_effects(results)
    effects.to_csv(args.output_dir / "effects_per_intervention.csv", index=False)
    generate_summary(effects, args.output_dir / "summary.md")

    print(f"[D-1.2] Outputs written to {args.output_dir}")
    print(f"[D-1.2] Cumulative budget: ${budget.cumulative_cost():.2f}")


if __name__ == "__main__":
    main()
