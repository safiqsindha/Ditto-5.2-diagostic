"""
Tests for D-1.1 Poker symbolic rule-checker
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1

Note: Poker is Tier 0 (saturated) in v5, so violations should be near-trivial to detect.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tier1.d_1_1_symbolic_detection.poker_rules import (
    check_chain,
    _check_card_duplicates,
    _check_stack_non_negative,
    _check_pot_non_negative,
    _check_bet_exceeds_stack,
    _check_community_card_count,
    _check_action_after_fold,
    _check_street_ordering,
)


def make_state(street=None, community_cards=None, players=None, pot=None, **kwargs):
    s = {}
    if street:
        s["street"] = street
    if community_cards is not None:
        s["community_cards"] = community_cards
    if players is not None:
        s["players"] = players
    if pot is not None:
        s["pot"] = pot
    s.update(kwargs)
    return s


def make_player(id="p1", stack=1000, action=None, bet_amount=None, hole_cards=None):
    p = {"id": id, "stack": stack}
    if action:
        p["action"] = action
    if bet_amount is not None:
        p["bet_amount"] = bet_amount
    if hole_cards:
        p["hole_cards"] = hole_cards
    return p


# --- POSITIVE CASES (violations) ---

class TestCardDuplicateViolations:
    def test_duplicate_community_card(self):
        chain = [make_state(
            street="flop",
            community_cards=["AH", "KD", "AH"],  # AH appears twice
        )]
        r = _check_card_duplicates(chain)
        assert r.violation
        assert r.violation_type == "duplicate_card"

    def test_community_and_hole_card_overlap(self):
        chain = [make_state(
            street="flop",
            community_cards=["AH", "KD", "QS"],
            players={"p1": make_player(hole_cards=["AH", "2C"])},  # AH duplicate
        )]
        r = _check_card_duplicates(chain)
        assert r.violation


class TestStackViolations:
    def test_negative_stack(self):
        chain = [make_state(players={"p1": make_player(stack=-100)})]
        r = _check_stack_non_negative(chain)
        assert r.violation

    def test_zero_stack_valid(self):
        chain = [make_state(players={"p1": make_player(stack=0)})]
        r = _check_stack_non_negative(chain)
        assert not r.violation


class TestPotViolations:
    def test_negative_pot(self):
        chain = [make_state(pot=-50)]
        r = _check_pot_non_negative(chain)
        assert r.violation


class TestBetExceedsStack:
    def test_bet_exceeds_stack_no_allin(self):
        chain = [make_state(players={
            "p1": make_player(stack=100, action="raise", bet_amount=200)
        })]
        r = _check_bet_exceeds_stack(chain)
        assert r.violation
        assert r.violation_type == "bet_exceeds_stack"


class TestCommunityCardCount:
    def test_too_many_on_flop(self):
        chain = [make_state(street="flop", community_cards=["AH", "KD", "QS", "JH"])]
        r = _check_community_card_count(chain)
        assert r.violation

    def test_too_many_on_preflop(self):
        chain = [make_state(street="preflop", community_cards=["AH"])]
        r = _check_community_card_count(chain)
        assert r.violation


class TestActionAfterFold:
    def test_raise_after_fold(self):
        chain = [
            make_state(players={"p1": make_player(action="fold")}),
            make_state(players={"p1": make_player(action="raise")}),
        ]
        r = _check_action_after_fold(chain)
        assert r.violation
        assert r.violation_type == "action_after_fold"


class TestStreetOrdering:
    def test_turn_before_flop(self):
        chain = [
            make_state(street="preflop"),
            make_state(street="turn"),   # skipped flop
            make_state(street="flop"),   # flop after turn → out of order
        ]
        r = _check_street_ordering(chain)
        assert r.violation

    def test_preflop_after_river(self):
        chain = [
            make_state(street="preflop"),
            make_state(street="flop"),
            make_state(street="turn"),
            make_state(street="river"),
            make_state(street="preflop"),  # reset → violation
        ]
        r = _check_street_ordering(chain)
        assert r.violation


# --- NEGATIVE CASES (clean chains) ---

class TestCleanPokerChains:
    def test_normal_hand(self):
        chain = [
            make_state(street="preflop",
                       community_cards=[],
                       players={"p1": make_player(action="raise", bet_amount=20),
                                "p2": make_player(action="call", bet_amount=20)},
                       pot=40),
            make_state(street="flop",
                       community_cards=["AH", "KD", "QS"],
                       players={"p1": make_player(action="bet", bet_amount=30),
                                "p2": make_player(action="call", bet_amount=30)},
                       pot=100),
            make_state(street="turn",
                       community_cards=["AH", "KD", "QS", "JH"],
                       pot=100),
            make_state(street="river",
                       community_cards=["AH", "KD", "QS", "JH", "2C"],
                       pot=100),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_fold_is_terminal(self):
        chain = [
            make_state(players={"p1": make_player(id="p1", action="call"),
                                "p2": make_player(id="p2", action="fold")}),
            # p2 no longer acts after folding — only p1 present in next state
            make_state(players={"p1": make_player(id="p1", action="bet")}),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_all_in_can_exceed_stack(self):
        """All-in is exempt from bet-exceeds-stack check."""
        chain = [make_state(players={
            "p1": {"id": "p1", "stack": 100, "action": "all_in",
                   "bet_amount": 200, "all_in": True}
        })]
        r = check_chain(chain)
        assert not r.violation

    def test_correct_street_ordering(self):
        streets = ["preflop", "flop", "turn", "river", "showdown"]
        chain = [make_state(street=s) for s in streets]
        r = _check_street_ordering(chain)
        assert not r.violation

    def test_five_community_cards_on_river(self):
        chain = [make_state(street="river",
                            community_cards=["AH", "KD", "QS", "JH", "2C"])]
        r = _check_community_card_count(chain)
        assert not r.violation

    def test_empty_chain(self):
        r = check_chain([])
        assert not r.violation
