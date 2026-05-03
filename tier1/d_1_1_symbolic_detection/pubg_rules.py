"""
D-1.1: Symbolic rule-checker for PUBG chains
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Input: a chain (list of state dicts) representing a PUBG game sequence.
Output: ViolationResult with fields:
    - violation: bool
    - violation_type: str | None
    - position: int | None  (index of first violating element)
    - details: str

Rule coverage is aligned with v5 chain construction constraints.
Update rules here if v5 chain docs reveal additional constraints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ViolationResult:
    violation: bool
    violation_type: str | None = None
    position: int | None = None
    details: str = ""


def check_chain(chain: list[dict[str, Any]]) -> ViolationResult:
    """
    Entry point for PUBG rule checking.

    Applies all rules in order; returns on first detected violation.
    """
    for check_fn in [
        _check_health_bounds,
        _check_armor_bounds,
        _check_ammo_non_negative,
        _check_dead_player_acts,
        _check_score_monotone,
        _check_healing_precondition,
        _check_zone_damage_direction,
        _check_player_count_non_increasing,
    ]:
        result = check_fn(chain)
        if result.violation:
            return result
    return ViolationResult(violation=False, details="No violations detected")


# ---------------------------------------------------------------------------
# Individual rule functions
# ---------------------------------------------------------------------------

def _check_health_bounds(chain: list[dict]) -> ViolationResult:
    """Health must be in [0, 100] at all times."""
    for i, state in enumerate(chain):
        for player_key in _player_keys(state):
            hp = _get(state, player_key, "health")
            if hp is None:
                continue
            if not (0 <= hp <= 100):
                return ViolationResult(
                    violation=True,
                    violation_type="health_out_of_bounds",
                    position=i,
                    details=f"Player {player_key} health={hp} not in [0,100] at position {i}",
                )
    return ViolationResult(violation=False)


def _check_armor_bounds(chain: list[dict]) -> ViolationResult:
    """Armor must be in [0, 300] (Level 3 vest max = 200; helmet adds up to 150 — use 300 as ceiling)."""
    for i, state in enumerate(chain):
        for player_key in _player_keys(state):
            armor = _get(state, player_key, "armor")
            if armor is None:
                continue
            if not (0 <= armor <= 300):
                return ViolationResult(
                    violation=True,
                    violation_type="armor_out_of_bounds",
                    position=i,
                    details=f"Player {player_key} armor={armor} not in [0,300] at position {i}",
                )
    return ViolationResult(violation=False)


def _check_ammo_non_negative(chain: list[dict]) -> ViolationResult:
    """Ammo counts must be non-negative."""
    for i, state in enumerate(chain):
        for player_key in _player_keys(state):
            ammo = _get(state, player_key, "ammo")
            if ammo is None:
                continue
            if ammo < 0:
                return ViolationResult(
                    violation=True,
                    violation_type="ammo_negative",
                    position=i,
                    details=f"Player {player_key} ammo={ammo} < 0 at position {i}",
                )
    return ViolationResult(violation=False)


def _check_dead_player_acts(chain: list[dict]) -> ViolationResult:
    """A player with health=0 (dead) cannot perform actions in later states."""
    dead_players: set[str] = set()
    for i, state in enumerate(chain):
        for player_key in _player_keys(state):
            hp = _get(state, player_key, "health")
            if hp == 0:
                dead_players.add(player_key)
            elif player_key in dead_players and hp is not None and hp > 0:
                action = _get(state, player_key, "action")
                if action in ("revived", "respawned"):
                    dead_players.discard(player_key)  # properly revived
                else:
                    return ViolationResult(
                        violation=True,
                        violation_type="dead_player_active",
                        position=i,
                        details=(f"Player {player_key} was dead (health=0) "
                                 f"but has health={hp} without revive at position {i}"),
                    )
    return ViolationResult(violation=False)


def _check_score_monotone(chain: list[dict]) -> ViolationResult:
    """Kill score / points cannot decrease over time."""
    for player_key in _all_player_keys(chain):
        prev_score = None
        for i, state in enumerate(chain):
            score = _get(state, player_key, "kills")
            if score is None:
                score = _get(state, player_key, "score")
            if score is None:
                continue
            if prev_score is not None and score < prev_score:
                return ViolationResult(
                    violation=True,
                    violation_type="score_decreased",
                    position=i,
                    details=f"Player {player_key} score decreased from {prev_score} to {score} at {i}",
                )
            prev_score = score
    return ViolationResult(violation=False)


def _check_healing_precondition(chain: list[dict]) -> ViolationResult:
    """A healing action must occur when health < 100 (using healing at full health is a violation)."""
    for i, state in enumerate(chain):
        for player_key in _player_keys(state):
            action = _get(state, player_key, "action")
            if action in ("heal", "use_medkit", "use_bandage", "use_boost"):
                hp = _get(state, player_key, "health")
                if hp is not None and hp >= 100:
                    return ViolationResult(
                        violation=True,
                        violation_type="healing_at_full_health",
                        position=i,
                        details=f"Player {player_key} uses {action} at full health ({hp}) at position {i}",
                    )
    return ViolationResult(violation=False)


def _check_zone_damage_direction(chain: list[dict]) -> ViolationResult:
    """Zone damage (outside zone) can only reduce health, not increase it."""
    for i in range(1, len(chain)):
        prev, curr = chain[i - 1], chain[i]
        for player_key in _player_keys(curr):
            in_zone = _get(curr, player_key, "in_zone")
            if in_zone is False:
                prev_hp = _get(prev, player_key, "health")
                curr_hp = _get(curr, player_key, "health")
                if prev_hp is not None and curr_hp is not None and curr_hp > prev_hp:
                    return ViolationResult(
                        violation=True,
                        violation_type="zone_damage_health_increase",
                        position=i,
                        details=(f"Player {player_key} outside zone but health increased "
                                 f"from {prev_hp} to {curr_hp} at position {i}"),
                    )
    return ViolationResult(violation=False)


def _check_player_count_non_increasing(chain: list[dict]) -> ViolationResult:
    """Total alive player count can only stay same or decrease (no respawns in standard PUBG).
    Revives (knocked → alive again) are permitted."""
    prev_count = None
    for i, state in enumerate(chain):
        alive_keys = [k for k in _player_keys(state)
                      if (_get(state, k, "health") or 0) > 0]
        count = state.get("alive_count", len(alive_keys))
        # Allow increase if any player action is revive/respawn
        has_revive = any(
            _get(state, k, "action") in ("revived", "respawned")
            for k in _player_keys(state)
        )
        if prev_count is not None and count > prev_count and not has_revive:
            return ViolationResult(
                violation=True,
                violation_type="alive_count_increased",
                position=i,
                details=f"Alive player count increased from {prev_count} to {count} at position {i}",
            )
        if count >= 0:
            prev_count = count
    return ViolationResult(violation=False)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _player_keys(state: dict) -> list[str]:
    """Return list of player keys in a state dict (player_1, player_2, etc.)."""
    return [k for k in state if k.startswith("player") or k in ("attacker", "victim")]


def _all_player_keys(chain: list[dict]) -> set[str]:
    keys: set[str] = set()
    for state in chain:
        keys.update(_player_keys(state))
    return keys


def _get(state: dict, player_key: str, field: str) -> Any:
    """Get a field from player sub-dict or top-level state."""
    player_data = state.get(player_key)
    if isinstance(player_data, dict):
        return player_data.get(field)
    return state.get(f"{player_key}_{field}")
