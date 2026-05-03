"""
D-1.1: Symbolic rule-checker for CS:GO chains
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Rules cover CS:GO round sequences: economy, buy phase, bomb mechanics,
player counts, and round structure.
"""
from __future__ import annotations

from typing import Any

from tier1.d_1_1_symbolic_detection.pubg_rules import ViolationResult

MAX_PLAYERS_PER_TEAM = 5
MAX_MONEY = 16000
MIN_MONEY = 0
BUY_PHASE_DURATION_SECONDS = 20
BOMB_PLANT_DURATION_SECONDS = 3
BOMB_DEFUSE_DURATION_SECONDS = 10  # 5 with kit
ROUND_TIME_SECONDS = 115


def check_chain(chain: list[dict[str, Any]]) -> ViolationResult:
    for check_fn in [
        _check_money_bounds,
        _check_buy_phase_purchases,
        _check_dead_player_acts,
        _check_bomb_state_transitions,
        _check_team_size,
        _check_round_structure,
    ]:
        result = check_fn(chain)
        if result.violation:
            return result
    return ViolationResult(violation=False, details="No violations detected")


def _check_money_bounds(chain: list[dict]) -> ViolationResult:
    """Player money must be in [0, 16000]."""
    for i, state in enumerate(chain):
        for team in ("ct", "t"):
            players = state.get(f"{team}_players", [])
            if not isinstance(players, list):
                players = [players] if isinstance(players, dict) else []
            for player in players:
                if not isinstance(player, dict):
                    continue
                money = player.get("money")
                if money is not None and not (MIN_MONEY <= money <= MAX_MONEY):
                    return ViolationResult(
                        violation=True,
                        violation_type="money_out_of_bounds",
                        position=i,
                        details=f"Player money={money} not in [0,16000] at position {i}",
                    )
    return ViolationResult(violation=False)


def _check_buy_phase_purchases(chain: list[dict]) -> ViolationResult:
    """Players cannot buy equipment outside the buy phase."""
    for i, state in enumerate(chain):
        in_buy_phase = state.get("buy_phase", True)
        if in_buy_phase:
            continue
        event = state.get("event")
        if event in ("buy_rifle", "buy_pistol", "buy_armor", "buy_grenade", "buy_kit"):
            return ViolationResult(
                violation=True,
                violation_type="purchase_outside_buy_phase",
                position=i,
                details=f"Purchase event '{event}' occurred outside buy phase at position {i}",
            )
    return ViolationResult(violation=False)


def _check_dead_player_acts(chain: list[dict]) -> ViolationResult:
    """A dead player cannot shoot, plant, defuse, or buy."""
    active_actions = {"shoot", "plant", "defuse", "buy_rifle", "throw_grenade", "move"}
    dead_players: set[str] = set()

    for i, state in enumerate(chain):
        for team in ("ct_players", "t_players"):
            players = state.get(team, [])
            if isinstance(players, dict):
                players = list(players.values())
            for player in (players if isinstance(players, list) else []):
                if not isinstance(player, dict):
                    continue
                pid = player.get("id", str(player))
                hp = player.get("health", player.get("hp"))
                action = player.get("action")

                if hp == 0:
                    dead_players.add(str(pid))
                elif str(pid) in dead_players and (hp or 0) > 0:
                    dead_players.discard(str(pid))

                if str(pid) in dead_players and action in active_actions:
                    return ViolationResult(
                        violation=True,
                        violation_type="dead_player_acts",
                        position=i,
                        details=f"Dead player {pid} performs action '{action}' at position {i}",
                    )
    return ViolationResult(violation=False)


def _check_bomb_state_transitions(chain: list[dict]) -> ViolationResult:
    """
    Bomb state must follow valid transitions:
    none → planted → (defused | exploded)
    Exploded bomb cannot be defused. Defused bomb cannot explode.
    """
    VALID_TRANSITIONS = {
        None: {"planted", None},
        "planted": {"defused", "exploded", "planted"},
        "defused": {"defused"},
        "exploded": {"exploded"},
    }
    prev_bomb = None
    for i, state in enumerate(chain):
        bomb_state = state.get("bomb_state")
        if bomb_state is None:
            bomb_state = None
        valid = VALID_TRANSITIONS.get(prev_bomb, set())
        if bomb_state not in valid:
            return ViolationResult(
                violation=True,
                violation_type="invalid_bomb_transition",
                position=i,
                details=f"Bomb state transition {prev_bomb!r} → {bomb_state!r} is invalid at position {i}",
            )
        prev_bomb = bomb_state
    return ViolationResult(violation=False)


def _check_team_size(chain: list[dict]) -> ViolationResult:
    """Each team can have at most 5 players alive at any point."""
    for i, state in enumerate(chain):
        for team_key in ("ct_alive", "t_alive"):
            count = state.get(team_key)
            if count is not None and count > MAX_PLAYERS_PER_TEAM:
                return ViolationResult(
                    violation=True,
                    violation_type="team_too_large",
                    position=i,
                    details=f"{team_key}={count} exceeds max {MAX_PLAYERS_PER_TEAM} at position {i}",
                )
    return ViolationResult(violation=False)


def _check_round_structure(chain: list[dict]) -> ViolationResult:
    """Round number must be non-decreasing."""
    prev_round = None
    for i, state in enumerate(chain):
        rnd = state.get("round")
        if rnd is None:
            continue
        if prev_round is not None and rnd < prev_round:
            return ViolationResult(
                violation=True,
                violation_type="round_number_decreased",
                position=i,
                details=f"Round decreased from {prev_round} to {rnd} at position {i}",
            )
        prev_round = rnd
    return ViolationResult(violation=False)
