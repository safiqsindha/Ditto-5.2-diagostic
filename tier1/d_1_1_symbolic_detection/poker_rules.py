"""
D-1.1: Symbolic rule-checker for Poker chains
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Coverage note: Poker is Tier 0 (saturated) in v5, so symbolic detection
should be near-trivial. This is documented per pre-reg §3.3.1.

Rules cover: card deck integrity, betting constraints, pot mechanics,
hand structure, and action validity.
"""
from __future__ import annotations

from typing import Any

from tier1.d_1_1_symbolic_detection.pubg_rules import ViolationResult

DECK_SIZE = 52
SUITS = {"hearts", "diamonds", "clubs", "spades"}
RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}
VALID_STREETS = {"preflop", "flop", "turn", "river", "showdown"}
VALID_ACTIONS = {"fold", "check", "call", "raise", "bet", "all_in"}
MAX_COMMUNITY_CARDS = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}


def check_chain(chain: list[dict[str, Any]]) -> ViolationResult:
    for check_fn in [
        _check_card_duplicates,
        _check_stack_non_negative,
        _check_pot_non_negative,
        _check_bet_exceeds_stack,
        _check_community_card_count,
        _check_action_after_fold,
        _check_street_ordering,
    ]:
        result = check_fn(chain)
        if result.violation:
            return result
    return ViolationResult(
        violation=False,
        details="No violations detected. Note: Poker is Tier 0 saturated — detection may be trivial.",
    )


def _check_card_duplicates(chain: list[dict]) -> ViolationResult:
    """No card should appear more than once across all visible cards at any state."""
    for i, state in enumerate(chain):
        all_cards = _collect_all_cards(state)
        seen: set[str] = set()
        for card in all_cards:
            norm = _normalize_card(card)
            if norm and norm in seen:
                return ViolationResult(
                    violation=True,
                    violation_type="duplicate_card",
                    position=i,
                    details=f"Card {norm!r} appears more than once at position {i}",
                )
            if norm:
                seen.add(norm)
    return ViolationResult(violation=False)


def _check_stack_non_negative(chain: list[dict]) -> ViolationResult:
    """Player chip stacks must be non-negative."""
    for i, state in enumerate(chain):
        for player in _get_players(state):
            stack = player.get("stack") or player.get("chips")
            if stack is not None and stack < 0:
                return ViolationResult(
                    violation=True,
                    violation_type="negative_stack",
                    position=i,
                    details=f"Player {player.get('id', '?')} has stack={stack} < 0 at position {i}",
                )
    return ViolationResult(violation=False)


def _check_pot_non_negative(chain: list[dict]) -> ViolationResult:
    """Pot must be non-negative."""
    for i, state in enumerate(chain):
        pot = state.get("pot") or state.get("pot_size")
        if pot is not None and pot < 0:
            return ViolationResult(
                violation=True,
                violation_type="negative_pot",
                position=i,
                details=f"Pot={pot} < 0 at position {i}",
            )
    return ViolationResult(violation=False)


def _check_bet_exceeds_stack(chain: list[dict]) -> ViolationResult:
    """A non-all-in bet cannot exceed the player's current stack."""
    for i, state in enumerate(chain):
        for player in _get_players(state):
            action = player.get("action")
            if action not in ("raise", "bet", "call"):
                continue
            amount = player.get("bet_amount") or player.get("amount")
            stack = player.get("stack") or player.get("chips")
            is_all_in = player.get("all_in", False) or action == "all_in"
            if amount is not None and stack is not None and not is_all_in:
                if amount > stack:
                    return ViolationResult(
                        violation=True,
                        violation_type="bet_exceeds_stack",
                        position=i,
                        details=(f"Player {player.get('id', '?')} bets {amount} "
                                 f"but only has stack={stack} at position {i}"),
                    )
    return ViolationResult(violation=False)


def _check_community_card_count(chain: list[dict]) -> ViolationResult:
    """Community card count must match the street."""
    for i, state in enumerate(chain):
        street = state.get("street")
        if street not in MAX_COMMUNITY_CARDS:
            continue
        community = state.get("community_cards", [])
        if isinstance(community, list):
            n = len([c for c in community if c])
            max_n = MAX_COMMUNITY_CARDS[street]
            if n > max_n:
                return ViolationResult(
                    violation=True,
                    violation_type="too_many_community_cards",
                    position=i,
                    details=f"Street={street} has {n} community cards (max {max_n}) at position {i}",
                )
    return ViolationResult(violation=False)


def _check_action_after_fold(chain: list[dict]) -> ViolationResult:
    """A folded player cannot take further actions."""
    folded: set[str] = set()
    for i, state in enumerate(chain):
        for player in _get_players(state):
            pid = str(player.get("id", id(player)))
            action = player.get("action")
            if action == "fold":
                folded.add(pid)
            elif pid in folded and action in VALID_ACTIONS - {"fold"}:
                return ViolationResult(
                    violation=True,
                    violation_type="action_after_fold",
                    position=i,
                    details=f"Player {pid} took action '{action}' after folding at position {i}",
                )
    return ViolationResult(violation=False)


def _check_street_ordering(chain: list[dict]) -> ViolationResult:
    """Street must follow preflop → flop → turn → river → showdown ordering."""
    STREET_ORDER = ["preflop", "flop", "turn", "river", "showdown"]
    prev_idx = None
    for i, state in enumerate(chain):
        street = state.get("street")
        if street not in STREET_ORDER:
            continue
        curr_idx = STREET_ORDER.index(street)
        if prev_idx is not None and curr_idx < prev_idx:
            return ViolationResult(
                violation=True,
                violation_type="street_out_of_order",
                position=i,
                details=f"Street went from {STREET_ORDER[prev_idx]!r} back to {street!r} at position {i}",
            )
        prev_idx = curr_idx
    return ViolationResult(violation=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_players(state: dict) -> list[dict]:
    players = state.get("players", [])
    if isinstance(players, dict):
        return list(players.values())
    return players if isinstance(players, list) else []


def _collect_all_cards(state: dict) -> list[str]:
    cards = list(state.get("community_cards", []))
    for player in _get_players(state):
        if isinstance(player, dict):
            hole = player.get("hole_cards") or player.get("hand", [])
            if isinstance(hole, list):
                cards.extend(hole)
    return [c for c in cards if c]


def _normalize_card(card: Any) -> str | None:
    if isinstance(card, dict):
        rank = str(card.get("rank", ""))
        suit = str(card.get("suit", "")).lower()
        return f"{rank}{suit}" if rank and suit else None
    if isinstance(card, str) and len(card) >= 2:
        return card.strip().upper()
    return None
