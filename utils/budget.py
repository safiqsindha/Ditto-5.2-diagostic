"""
Budget tracker for Tier 1 API calls.

Hard cap: $150 (Tier 1 total).
Alert at: 75% of mid-estimate ($75), or 150% of per-diagnostic mid-estimate.

Usage:
    tracker = BudgetTracker()
    tracker.log("d_1_2", "gpt-5", prompt_tokens=500, completion_tokens=100, cost=0.02)
    tracker.check_alert()
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

BUDGET_FILE = Path("budget_tracker.csv")
TIER1_HARD_CAP = 150.0
TIER1_MID_ESTIMATE = 75.0

DIAGNOSTIC_MID_ESTIMATES = {
    "d_1_2": 40.0,
    "d_1_3": 20.0,
    "d_1_4": 15.0,
}


class BudgetTracker:
    def __init__(self, budget_file: Path = BUDGET_FILE):
        self.budget_file = budget_file
        self._ensure_header()

    def _ensure_header(self):
        if not self.budget_file.exists() or self.budget_file.stat().st_size == 0:
            with open(self.budget_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "diagnostic", "model",
                    "prompt_tokens", "completion_tokens",
                    "cost_estimate", "cumulative_cost",
                ])

    def cumulative_cost(self) -> float:
        if not self.budget_file.exists():
            return 0.0
        total = 0.0
        with open(self.budget_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    total += float(row["cost_estimate"])
                except (ValueError, KeyError):
                    pass
        return total

    def diagnostic_cost(self, diagnostic: str) -> float:
        if not self.budget_file.exists():
            return 0.0
        total = 0.0
        with open(self.budget_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("diagnostic") == diagnostic:
                    try:
                        total += float(row["cost_estimate"])
                    except (ValueError, KeyError):
                        pass
        return total

    def log(
        self,
        diagnostic: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
    ):
        cumulative = self.cumulative_cost() + cost
        with open(self.budget_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                diagnostic,
                model,
                prompt_tokens,
                completion_tokens,
                f"{cost:.6f}",
                f"{cumulative:.6f}",
            ])
        self.check_alert(cumulative=cumulative, diagnostic=diagnostic)

    def check_alert(self, cumulative: float | None = None, diagnostic: str | None = None):
        if cumulative is None:
            cumulative = self.cumulative_cost()

        if cumulative >= TIER1_HARD_CAP:
            print(
                f"\n[BUDGET HALT] Tier 1 cumulative cost ${cumulative:.2f} "
                f"exceeds hard cap ${TIER1_HARD_CAP:.0f}. Halting. "
                "An amendment is required before continuing.",
                file=sys.stderr,
            )
            sys.exit(1)

        if cumulative >= TIER1_MID_ESTIMATE:
            print(
                f"[BUDGET ALERT] Cumulative cost ${cumulative:.2f} "
                f"exceeds 75% of mid-estimate (${TIER1_MID_ESTIMATE:.0f}).",
                file=sys.stderr,
            )

        if diagnostic and diagnostic in DIAGNOSTIC_MID_ESTIMATES:
            diag_cost = self.diagnostic_cost(diagnostic)
            mid = DIAGNOSTIC_MID_ESTIMATES[diagnostic]
            if diag_cost >= mid * 1.5:
                print(
                    f"[BUDGET ALERT] {diagnostic} cost ${diag_cost:.2f} "
                    f"exceeds 150% of mid-estimate (${mid:.0f}).",
                    file=sys.stderr,
                )
