#!/usr/bin/env python3
"""
DDK v0.1 — local workflow runner.

Run this from the repo root at any point to see what's done,
what's next, and to execute the next step interactively.

    python3 next_steps.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent
DATA_RAW = REPO / "data/v5.1_raw/v51_raw.csv"
DATA_CORPUS = REPO / "data/v5_corpus"
TIER0_SUMMARY = REPO / "tier0_outputs/tier0_summary.md"
INTERIM_MEMO = REPO / "synthesis/interim_memo_post_tier0.md"
TIER1_SUMMARY = REPO / "tier1_outputs/tier1_summary.md"
DECISION_LOG = REPO / "prereg/decision_log.md"

TIDY_LONG_DEFAULT = (
    Path.home()
    / "Desktop/Project Ditto/Ditto V5.1 Final"
    / "03_analysis_outputs/phase3_consolidated/tidy_long.csv"
)

GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}!{RESET} {msg}")
def todo(msg): print(f"  {RED}→{RESET} {BOLD}{msg}{RESET}")


def run(cmd: list[str]) -> int:
    print(f"\n  $ {' '.join(str(c) for c in cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO)
    return result.returncode


def confirm(prompt: str) -> bool:
    ans = input(f"\n{BOLD}{prompt}{RESET} [y/N] ").strip().lower()
    return ans == "y"


def memo_is_signed() -> bool:
    if not INTERIM_MEMO.exists():
        return False
    text = INTERIM_MEMO.read_text()
    return "UNSIGNED" not in text and "________________" not in text


def check_state() -> dict:
    data_converted = DATA_RAW.exists()
    # Tier 0 is only "done" if real data exists AND the summary was produced
    # after it (summary mtime > data mtime means it was re-run on real data)
    tier0_real = (
        data_converted
        and TIER0_SUMMARY.exists()
        and TIER0_SUMMARY.stat().st_mtime >= DATA_RAW.stat().st_mtime
    ) if data_converted and TIER0_SUMMARY.exists() else False
    # Tier 1 is done when its summary exists and shows non-zero cost
    tier1_real = (
        TIER1_SUMMARY.exists()
        and "$0.00" not in TIER1_SUMMARY.read_text()
    ) if TIER1_SUMMARY.exists() else False
    return {
        "git_pulled":     True,
        "data_converted": data_converted,
        "tier0_done":     tier0_real,
        "memo_signed":    memo_is_signed(),
        "tier1_done":     tier1_real,
    }


def step_convert_data():
    print(f"\n{BOLD}Step 1 — Convert v5.1 data to DDK format{RESET}")
    tidy = TIDY_LONG_DEFAULT
    if not tidy.exists():
        custom = input(
            f"\n  Default path not found:\n  {tidy}\n\n"
            "  Enter path to tidy_long.csv: "
        ).strip().strip("'\"")
        tidy = Path(custom)
    if not tidy.exists():
        print(f"\n  {RED}File not found: {tidy}{RESET}")
        sys.exit(1)

    out = DATA_RAW
    if confirm(f"Run adapter → {out}?"):
        rc = run([sys.executable, "utils/v51_adapter.py",
                  "--input", str(tidy), "--output", str(out)])
        if rc != 0:
            print(f"\n  {RED}Adapter failed (exit {rc}){RESET}")
            sys.exit(1)
        ok(f"Data written to {out}")


def step_run_tier0():
    print(f"\n{BOLD}Step 2 — Run Tier 0 pipeline on real data{RESET}")
    warn("This reads data/v5.1_raw/v51_raw.csv. No API calls — pure analysis.")
    if confirm("Run tier0/tier0_pipeline.py?"):
        rc = run([sys.executable, "tier0/tier0_pipeline.py",
                  "--data-dir", str(DATA_RAW.parent)])
        if rc != 0:
            print(f"\n  {RED}Tier 0 failed (exit {rc}){RESET}")
            sys.exit(1)
        ok("Tier 0 complete — outputs in tier0_outputs/")
        print(f"\n  Open {REPO / 'tier0_outputs/tier0_summary.md'} to review results.")


def step_sign_memo():
    print(f"\n{BOLD}Step 3 — Sign the interim memo{RESET}")
    warn("Tier 1 is BLOCKED until both authors sign synthesis/interim_memo_post_tier0.md")
    print(f"\n  File: {INTERIM_MEMO}")
    print("  Replace the UNSIGNED placeholder lines with your names and today's date.")
    print("  Then re-run this script.")
    input("\n  Press Enter when you've opened the file... ")


def step_run_tier1():
    print(f"\n{BOLD}Step 4 — Run Tier 1 pipeline{RESET}")
    warn("This makes REAL API calls (~$30-150). Ensure API keys are set:")
    print("    ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY")
    warn("PLACEHOLDER prompts in d_1_2/d_1_3/d_1_4 must be filled before running.")
    if confirm("Run tier1/tier1_pipeline.py?"):
        rc = run([sys.executable, "tier1/tier1_pipeline.py",
                  "--data-dir", str(DATA_RAW.parent),
                  "--corpus-dir", str(DATA_CORPUS)])
        if rc != 0:
            print(f"\n  {RED}Tier 1 failed (exit {rc}){RESET}")
            sys.exit(1)
        ok("Tier 1 complete — outputs in tier1_outputs/")


def main():
    print(f"\n{BOLD}═══ DDK v0.1 — Next Steps ═══{RESET}\n")

    state = check_state()

    # Status board
    ok("Repo cloned and pre-reg signed (Entry 002 logged)")                if True else None
    ok("Data converted → data/v5.1_raw/v51_raw.csv")                       if state["data_converted"] else warn("Data not yet converted")
    ok("Tier 0 complete — real data run")                                   if state["tier0_done"] else warn("Tier 0 not yet run on real data")
    ok("Interim memo signed")                                               if state["memo_signed"] else warn("Interim memo UNSIGNED (blocks Tier 1)")
    ok("Tier 1 complete")                                                   if state["tier1_done"] else warn("Tier 1 not yet run")

    print()

    # Route to next step
    if not state["data_converted"]:
        todo("Next: convert v5.1 data")
        step_convert_data()
    elif not state["tier0_done"]:
        todo("Next: run Tier 0 on real data")
        step_run_tier0()
    elif not state["memo_signed"]:
        todo("Next: sign the interim memo")
        step_sign_memo()
    elif not state["tier1_done"]:
        todo("Next: run Tier 1")
        step_run_tier1()
    else:
        ok("All steps complete!")
        print(f"\n  Final outputs:")
        print(f"    {REPO / 'tier0_outputs/tier0_summary.md'}")
        print(f"    {REPO / 'tier1_outputs/tier1_summary.md'}")
        print(f"\n  Next: fill in synthesis/synthesis_v0.1.md and sign off.")

    print()


if __name__ == "__main__":
    main()
