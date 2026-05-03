"""
Tier 0 pipeline orchestrator
Pre-reg reference: DDK_v0.1_PREREG.md §3.1, Build Plan §2.1

Runs all five Tier 0 diagnostics in order. Each diagnostic writes its own
outputs. This pipeline:
  1. Verifies data availability
  2. Runs D-0.1 through D-0.5
  3. Generates tier0_outputs/tier0_summary.md (factual, no interpretation)

Usage:
    python tier0/tier0_pipeline.py [--test] [--only D-0.1 D-0.3 ...]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DATA_V51 = ROOT / "data/v5.1_raw"
DATA_V5_CORPUS = ROOT / "data/v5_corpus"
OUTPUT_ROOT = ROOT / "tier0_outputs"

DIAGNOSTICS = [
    ("D-0.1", "tier0/d_0_1_per_cell_breakdown.py"),
    ("D-0.2", "tier0/d_0_2_confusion_matrix.py"),
    ("D-0.3", "tier0/d_0_3_power_audit.py"),
    ("D-0.4", "tier0/d_0_4_confound_check.py"),
    ("D-0.5", "tier0/d_0_5_output_structure.py"),
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_data_availability(test_mode: bool) -> bool:
    if test_mode:
        return True
    v51_files = list(DATA_V51.glob("*.csv"))
    v5_files = list(DATA_V5_CORPUS.glob("*.csv")) + list(DATA_V5_CORPUS.glob("*.jsonl"))

    ok = True
    if not v51_files:
        print(f"[PIPELINE] WARNING: No v5.1 data found in {DATA_V51}", file=sys.stderr)
        ok = False
    if not v5_files:
        print(f"[PIPELINE] WARNING: No v5 corpus data found in {DATA_V5_CORPUS}", file=sys.stderr)
        ok = False
    return ok


def run_diagnostic(label: str, script: str, extra_args: list[str]) -> tuple[bool, float]:
    script_path = ROOT / script
    cmd = [sys.executable, str(script_path)] + extra_args
    print(f"\n[PIPELINE] Starting {label} ...")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"[PIPELINE] {label} FAILED (exit code {result.returncode})")
        return False, elapsed

    print(f"[PIPELINE] {label} complete in {elapsed:.1f}s")
    return True, elapsed


def collect_diagnostic_summaries() -> dict[str, str]:
    summaries = {}
    for label, _ in DIAGNOSTICS:
        key = label.lower().replace("-", "_").replace(".", "_")
        summary_path = OUTPUT_ROOT / key / "summary.md"
        if summary_path.exists():
            summaries[label] = summary_path.read_text()
        else:
            summaries[label] = f"_Summary not found at {summary_path}_"
    return summaries


def write_tier0_summary(
    results: dict[str, tuple[bool, float]],
    summaries: dict[str, str],
    output_path: Path,
):
    lines = [
        "# Tier 0 Summary",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n## Pipeline run results",
    ]
    for label, (ok, elapsed) in results.items():
        status = "OK" if ok else "FAILED"
        lines.append(f"- {label}: {status} ({elapsed:.1f}s)")

    for label, summary_text in summaries.items():
        lines.append(f"\n---\n\n## {label} summary\n")
        lines.append(summary_text)

    lines += [
        "\n---",
        "\n_This document is auto-generated and factual only._",
        "_Interpretation is deferred to authors (see synthesis/interim_memo_post_tier0.md)._",
    ]
    output_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Tier 0 pipeline")
    parser.add_argument("--test", action="store_true", help="Run all diagnostics in --test mode")
    parser.add_argument("--only", nargs="+", metavar="DIAG",
                        help="Run only specified diagnostics (e.g. D-0.1 D-0.3)")
    args = parser.parse_args()

    print(f"[PIPELINE] Tier 0 pipeline starting — {datetime.now(timezone.utc).isoformat()}")

    if not check_data_availability(args.test):
        if not args.test:
            print("[PIPELINE] Data check failed. Re-run with --test for dry-run mode.")
            sys.exit(1)

    pipeline_hash = sha256_file(ROOT / "tier0/tier0_pipeline.py")
    print(f"[PIPELINE] Pipeline script SHA-256: {pipeline_hash}")
    print(f"[PIPELINE] Record this in decision_log.md before first real run.")

    to_run = [(label, script) for label, script in DIAGNOSTICS
              if args.only is None or label in (args.only or [])]

    extra_args = ["--test"] if args.test else []
    run_results: dict[str, tuple[bool, float]] = {}

    for label, script in to_run:
        ok, elapsed = run_diagnostic(label, script, extra_args)
        run_results[label] = (ok, elapsed)

        if not ok:
            print(f"[PIPELINE] Halting after {label} failure per pre-reg §7 stopping rules.")
            break

    summaries = collect_diagnostic_summaries()
    output_path = OUTPUT_ROOT / "tier0_summary.md"
    write_tier0_summary(run_results, summaries, output_path)
    print(f"\n[PIPELINE] Tier 0 complete. Summary: {output_path}")

    failed = [l for l, (ok, _) in run_results.items() if not ok]
    if failed:
        print(f"[PIPELINE] Failed diagnostics: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
