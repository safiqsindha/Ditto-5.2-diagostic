"""
D-1.1: Symbolic rule-checker for NBA chains
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Rules cover NBA game-state sequences: scoring, fouls, shot clock,
quarter/period structure, and player foul limits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tier1.d_1_1_symbolic_detection.pubg_rules import ViolationResult

MAX_FOULS_PER_PLAYER = 6        # Disqualified on 6th personal foul
TEAM_FOUL_BONUS_THRESHOLD = 5   # Bonus free throws after 5 team fouls per half
POINTS_PER_FT = 1
POINTS_PER_2 = 2
POINTS_PER_3 = 3
VALID_SCORE_INCREMENTS = {0, 1, 2, 3}
MAX_QUARTERS = 4
QUARTER_DURATION_SECONDS = 720  # 12 min
SHOT_CLOCK_SECONDS = 24


def check_chain(chain: list[dict[str, Any]]) -> ViolationResult:
    for check_fn in [
        _check_score_monotone,
        _check_score_increment,
        _check_foul_limit,
        _check_quarter_structure,
        _check_shot_clock,
        _check_time_non_increasing_within_quarter,
    ]:
        result = check_fn(chain)
        if result.violation:
            return result
    return ViolationResult(violation=False, details="No violations detected")


def _check_score_monotone(chain: list[dict]) -> ViolationResult:
    """Team scores must be non-decreasing."""
    for team in ("home_score", "away_score"):
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
    """Score increments must be 0, 1, 2, or 3 per state transition."""
    for team in ("home_score", "away_score"):
        prev = None
        for i in range(1, len(chain)):
            curr = chain[i].get(team)
            prev = chain[i - 1].get(team)
            if curr is None or prev is None:
                continue
            delta = curr - prev
            if delta not in VALID_SCORE_INCREMENTS:
                return ViolationResult(
                    violation=True,
                    violation_type="invalid_score_increment",
                    position=i,
                    details=f"{team} jumped by {delta} at position {i} (valid: 0,1,2,3)",
                )
    return ViolationResult(violation=False)


def _check_foul_limit(chain: list[dict]) -> ViolationResult:
    """A player with ≥6 fouls cannot play (must be disqualified)."""
    for i, state in enumerate(chain):
        players = state.get("players", {})
        if not isinstance(players, dict):
            continue
        for pid, pdata in players.items():
            if not isinstance(pdata, dict):
                continue
            fouls = pdata.get("personal_fouls", 0)
            active = pdata.get("on_court", True)
            if fouls >= MAX_FOULS_PER_PLAYER and active:
                return ViolationResult(
                    violation=True,
                    violation_type="fouled_out_player_active",
                    position=i,
                    details=f"Player {pid} has {fouls} fouls but is still on court at position {i}",
                )
    return ViolationResult(violation=False)


def _check_quarter_structure(chain: list[dict]) -> ViolationResult:
    """Quarter number must be 1–4 (or >4 only if overtime). Must not decrease."""
    prev_quarter = None
    for i, state in enumerate(chain):
        q = state.get("quarter") or state.get("period")
        if q is None:
            continue
        if prev_quarter is not None and q < prev_quarter:
            return ViolationResult(
                violation=True,
                violation_type="quarter_decreased",
                position=i,
                details=f"Quarter decreased from {prev_quarter} to {q} at position {i}",
            )
        prev_quarter = q
    return ViolationResult(violation=False)


def _check_shot_clock(chain: list[dict]) -> ViolationResult:
    """Shot clock must be in [0, 24]. Cannot increase mid-possession without reset trigger."""
    prev_shot_clock = None
    for i, state in enumerate(chain):
        sc = state.get("shot_clock")
        if sc is None:
            prev_shot_clock = None
            continue
        if not (0 <= sc <= SHOT_CLOCK_SECONDS):
            return ViolationResult(
                violation=True,
                violation_type="shot_clock_out_of_bounds",
                position=i,
                details=f"Shot clock={sc} not in [0,{SHOT_CLOCK_SECONDS}] at position {i}",
            )
        # Shot clock can only increase on possession change or violation reset
        if prev_shot_clock is not None:
            if sc > prev_shot_clock:
                reset_event = state.get("possession_change") or state.get("shot_clock_reset")
                if not reset_event:
                    return ViolationResult(
                        violation=True,
                        violation_type="shot_clock_increased_without_reset",
                        position=i,
                        details=(f"Shot clock increased from {prev_shot_clock} to {sc} "
                                 f"without possession change or reset at position {i}"),
                    )
        prev_shot_clock = sc
    return ViolationResult(violation=False)


def _check_time_non_increasing_within_quarter(chain: list[dict]) -> ViolationResult:
    """Game clock must be non-increasing within a quarter."""
    prev_q, prev_time = None, None
    for i, state in enumerate(chain):
        q = state.get("quarter") or state.get("period")
        t = state.get("game_clock") or state.get("time_remaining")
        if q is None or t is None:
            continue
        if q == prev_q and prev_time is not None and t > prev_time:
            return ViolationResult(
                violation=True,
                violation_type="game_clock_increased_within_quarter",
                position=i,
                details=(f"Game clock increased from {prev_time} to {t} "
                         f"within quarter {q} at position {i}"),
            )
        prev_q, prev_time = q, t
    return ViolationResult(violation=False)
