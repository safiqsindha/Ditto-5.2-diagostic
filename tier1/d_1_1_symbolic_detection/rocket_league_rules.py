"""
D-1.1: Symbolic rule-checker for Rocket League chains
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Coverage note: Rocket League is Tier 3 (misaligned) in v5; symbolic rules
may have low coverage. Gaps are documented per pre-reg §3.3.1.
"""
from __future__ import annotations

from typing import Any

from tier1.d_1_1_symbolic_detection.pubg_rules import ViolationResult

MAX_BOOST = 100
MIN_BOOST = 0
MIN_SCORE = 0
OVERTIME_THRESHOLD = 5 * 60  # 5 minutes in seconds


def check_chain(chain: list[dict[str, Any]]) -> ViolationResult:
    for check_fn in [
        _check_boost_bounds,
        _check_score_monotone,
        _check_score_increment,
        _check_time_non_increasing,
        _check_overtime_structure,
    ]:
        result = check_fn(chain)
        if result.violation:
            return result
    return ViolationResult(
        violation=False,
        details=(
            "No violations detected. "
            "COVERAGE NOTE: Rocket League rules have limited coverage "
            "due to continuous physics; violations may exist below detection threshold."
        ),
    )


def _check_boost_bounds(chain: list[dict]) -> ViolationResult:
    """Boost must be in [0, 100] for each player."""
    for i, state in enumerate(chain):
        for team in ("orange_players", "blue_players", "players"):
            players = state.get(team, [])
            if isinstance(players, dict):
                players = list(players.values())
            for player in (players if isinstance(players, list) else []):
                if not isinstance(player, dict):
                    continue
                boost = player.get("boost")
                if boost is None:
                    boost = player.get("boost_amount")
                if boost is not None and not (MIN_BOOST <= boost <= MAX_BOOST):
                    return ViolationResult(
                        violation=True,
                        violation_type="boost_out_of_bounds",
                        position=i,
                        details=f"Player boost={boost} not in [0,100] at position {i}",
                    )
    return ViolationResult(violation=False)


def _check_score_monotone(chain: list[dict]) -> ViolationResult:
    """Team scores must be non-decreasing (unless reset at match end — not in chain scope)."""
    for team in ("orange_score", "blue_score", "team_0_score", "team_1_score"):
        prev = None
        for i, state in enumerate(chain):
            score = state.get(team)
            if score is None:
                continue
            if prev is not None and score < prev:
                return ViolationResult(
                    violation=True,
                    violation_type="score_decreased",
                    position=i,
                    details=f"{team} decreased from {prev} to {score} at position {i}",
                )
            prev = score
    return ViolationResult(violation=False)


def _check_score_increment(chain: list[dict]) -> ViolationResult:
    """Scores increment by exactly 1 per goal."""
    for team in ("orange_score", "blue_score", "team_0_score", "team_1_score"):
        for i in range(1, len(chain)):
            prev_score = chain[i - 1].get(team)
            curr_score = chain[i].get(team)
            if prev_score is None or curr_score is None:
                continue
            delta = curr_score - prev_score
            if delta not in (0, 1):
                return ViolationResult(
                    violation=True,
                    violation_type="invalid_score_increment",
                    position=i,
                    details=f"{team} incremented by {delta} at position {i} (must be 0 or 1)",
                )
    return ViolationResult(violation=False)


def _check_time_non_increasing(chain: list[dict]) -> ViolationResult:
    """
    Game time remaining must be non-increasing within a period.
    Overtime resets are permitted if indicated by period_change event.
    """
    prev_time, prev_period = None, None
    for i, state in enumerate(chain):
        period = state.get("period", 1)
        t = state.get("time_remaining") or state.get("clock")
        if t is None:
            prev_time, prev_period = None, period
            continue
        if period == prev_period and prev_time is not None and t > prev_time:
            return ViolationResult(
                violation=True,
                violation_type="time_remaining_increased",
                position=i,
                details=(f"Time remaining increased from {prev_time} to {t} "
                         f"within period {period} at position {i}"),
            )
        prev_time, prev_period = t, period
    return ViolationResult(violation=False)


def _check_overtime_structure(chain: list[dict]) -> ViolationResult:
    """Overtime only triggers if scores are tied at end of regulation."""
    reg_end_states = [s for s in chain if s.get("period_end") and s.get("period", 1) == 1]
    ot_states = [s for s in chain if (s.get("period") or 1) > 1]

    if not ot_states:
        return ViolationResult(violation=False)

    if reg_end_states:
        last_reg = reg_end_states[-1]
        o_score = last_reg.get("orange_score") or last_reg.get("team_0_score")
        b_score = last_reg.get("blue_score") or last_reg.get("team_1_score")
        if o_score is not None and b_score is not None and o_score != b_score:
            return ViolationResult(
                violation=True,
                violation_type="overtime_without_tie",
                position=chain.index(ot_states[0]),
                details=f"Overtime state found but regulation ended {o_score}-{b_score} (not tied)",
            )
    return ViolationResult(violation=False)
