"""
Tier 1 pipeline orchestrator
Pre-reg reference: DDK_v0.1_PREREG.md §3.3, Build Plan §3

Runs all four Tier 1 diagnostics in order. IMPORTANT:
  - This pipeline MUST NOT run before the interim memo is signed
    (synthesis/interim_memo_post_tier0.md — pre-reg §4.1)
  - All prompt templates in D-1.2, D-1.3, D-1.4 must be reviewed/approved
    before the first live run
  - Budget is tracked in budget_tracker.csv; hard cap $150

Usage:
    python tier1/tier1_pipeline.py --dry-run   # verify setup without API calls
    python tier1/tier1_pipeline.py             # live run
    python tier1/tier1_pipeline.py --only D-1.1 D-1.4
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from utils.budget import BudgetTracker

OUTPUT_ROOT = ROOT / "tier1_outputs"
INTERIM_MEMO = ROOT / "synthesis/interim_memo_post_tier0.md"

DIAGNOSTICS = [
    ("D-1.1", "tier1/d_1_1_symbolic_detection/d_1_1_runner.py"),
    ("D-1.2", "tier1/d_1_2_baseline_intervention.py"),
    ("D-1.3", "tier1/d_1_3_format_variation.py"),
    ("D-1.4", "tier1/d_1_4_v1_replay.py"),
]


def check_interim_memo(force: bool = False):
    """Verify interim memo exists and has been signed before Tier 1 runs."""
    if force:
        return
    if not INTERIM_MEMO.exists():
        print(
            f"[PIPELINE] HALT: Interim memo not found at {INTERIM_MEMO}\n"
            "Per pre-reg §4.1: Tier 1 cannot begin until the interim memo is authored and signed.\n"
            "Use --force-no-memo to override (for dry-run testing only).",
            file=sys.stderr,
        )
        sys.exit(1)

    content = INTERIM_MEMO.read_text()
    if "PLACEHOLDER" in content or "UNSIGNED" in content or not content.strip():
        print(
            "[PIPELINE] HALT: Interim memo appears unsigned or incomplete.\n"
            "Both authors must sign before Tier 1 proceeds.",
            file=sys.stderr,
        )
        sys.exit(1)


def check_placeholder_prompts():
    """Warn if D-1.2 / D-1.3 / D-1.4 prompt templates still contain PLACEHOLDER text."""
    prompt_files = [
        ROOT / "tier1/d_1_2_baseline_intervention.py",
        ROOT / "tier1/d_1_3_format_variation.py",
        ROOT / "tier1/d_1_4_v1_replay.py",
    ]
    has_placeholder = False
    for f in prompt_files:
        if "PLACEHOLDER" in f.read_text():
            print(f"[PIPELINE] WARNING: {f.name} still contains PLACEHOLDER prompt text.")
            has_placeholder = True
    if has_placeholder:
        print("[PIPELINE] Prompt templates must be reviewed/approved before live run.")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_diagnostic(
    label: str,
    script: str,
    extra_args: list[str],
) -> tuple[bool, float]:
    script_path = ROOT / script
    cmd = [sys.executable, str(script_path)] + extra_args
    print(f"\n[PIPELINE] Starting {label}...")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"[PIPELINE] {label} FAILED (exit code {result.returncode})")
        return False, elapsed

    print(f"[PIPELINE] {label} complete in {elapsed:.1f}s")
    return True, elapsed


def collect_summaries() -> dict[str, str]:
    summaries = {}
    for label, _ in DIAGNOSTICS:
        key = label.lower().replace("-", "_").replace(".", "_")
        summary_path = OUTPUT_ROOT / key / "summary.md"
        if summary_path.exists():
            summaries[label] = summary_path.read_text()
        else:
            summaries[label] = f"_Summary not found at {summary_path}_"
    return summaries


def write_tier1_summary(
    results: dict[str, tuple[bool, float]],
    summaries: dict[str, str],
    output_path: Path,
    budget: BudgetTracker,
):
    lines = [
        "# Tier 1 Summary",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        f"\nTotal Tier 1 API cost: ${budget.cumulative_cost():.2f}",
        "\n## Pipeline run results",
    ]
    for label, (ok, elapsed) in results.items():
        lines.append(f"- {label}: {'OK' if ok else 'FAILED'} ({elapsed:.1f}s)")

    for label, text in summaries.items():
        lines.append(f"\n---\n\n## {label} summary\n")
        lines.append(text)

    lines += [
        "\n---",
        "\n_Auto-generated factual summary. Synthesis deferred to authors._",
        "_See synthesis/synthesis_v0.1.md for interpretation._",
    ]
    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Tier 1 pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="No API calls (--dry-run passed to each diagnostic)")
    parser.add_argument("--test", action="store_true",
                        help="Use synthetic data; no API calls")
    parser.add_argument("--only", nargs="+", metavar="DIAG",
                        help="Run only specified diagnostics (e.g. D-1.1 D-1.4)")
    parser.add_argument("--force-no-memo", action="store_true",
                        help="Skip interim memo check (for dry-run testing only)")
    args = parser.parse_args()

    print(f"[PIPELINE] Tier 1 pipeline starting — {datetime.now(timezone.utc).isoformat()}")

    check_interim_memo(force=args.force_no_memo or args.dry_run or args.test)

    if not args.dry_run and not args.test:
        check_placeholder_prompts()

    pipeline_hash = sha256_file(ROOT / "tier1/tier1_pipeline.py")
    print(f"[PIPELINE] Pipeline script SHA-256: {pipeline_hash}")
    print("[PIPELINE] Record this in decision_log.md before first real run.")

    to_run = [(label, script) for label, script in DIAGNOSTICS
              if args.only is None or label in (args.only or [])]

    extra_args = []
    if args.dry_run:
        extra_args.append("--dry-run")
    if args.test:
        extra_args.append("--test")

    budget = BudgetTracker()
    run_results: dict[str, tuple[bool, float]] = {}

    for label, script in to_run:
        ok, elapsed = run_diagnostic(label, script, extra_args)
        run_results[label] = (ok, elapsed)

        # Check budget after each Tier 1 diagnostic
        cum = budget.cumulative_cost()
        print(f"[PIPELINE] Cumulative cost after {label}: ${cum:.2f}")

        if not ok:
            print(f"[PIPELINE] Halting after {label} failure per pre-reg §7.")
            break

    summaries = collect_summaries()
    summary_path = OUTPUT_ROOT / "tier1_summary.md"
    write_tier1_summary(run_results, summaries, summary_path, budget)
    print(f"\n[PIPELINE] Tier 1 complete. Summary: {summary_path}")
    print(f"[PIPELINE] Total cost: ${budget.cumulative_cost():.2f}")

    failed = [l for l, (ok, _) in run_results.items() if not ok]
    if failed:
        print(f"[PIPELINE] Failed: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
