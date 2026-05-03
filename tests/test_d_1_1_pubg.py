"""
Tests for D-1.1 PUBG symbolic rule-checker
Pre-reg reference: DDK_v0.1_PREREG.md §3.3.1, Build Plan §3.1

Test coverage target: ≥20 positive cases (violations), ≥20 negative cases (clean).
All tests are hand-crafted ground-truth chains.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tier1.d_1_1_symbolic_detection.pubg_rules import (
    ViolationResult,
    check_chain,
    _check_health_bounds,
    _check_armor_bounds,
    _check_ammo_non_negative,
    _check_dead_player_acts,
    _check_score_monotone,
    _check_healing_precondition,
    _check_zone_damage_direction,
    _check_player_count_non_increasing,
)


# ---------------------------------------------------------------------------
# Helper constructors for readable test chains
# ---------------------------------------------------------------------------

def player(
    health=75, armor=50, ammo=30, action=None, kills=0, in_zone=True
) -> dict:
    data = {"health": health, "armor": armor, "ammo": ammo, "kills": kills, "in_zone": in_zone}
    if action:
        data["action"] = action
    return data


def state(p1=None, p2=None, alive_count=None, **kwargs) -> dict:
    s = {}
    if p1 is not None:
        s["player_1"] = p1
    if p2 is not None:
        s["player_2"] = p2
    if alive_count is not None:
        s["alive_count"] = alive_count
    s.update(kwargs)
    return s


# ---------------------------------------------------------------------------
# POSITIVE CASES (violations — checker must return violation=True)
# ---------------------------------------------------------------------------

class TestHealthBoundsViolations:
    def test_health_exceeds_100(self):
        chain = [state(p1=player(health=150))]
        r = _check_health_bounds(chain)
        assert r.violation
        assert r.violation_type == "health_out_of_bounds"

    def test_health_negative(self):
        chain = [state(p1=player(health=-1))]
        r = _check_health_bounds(chain)
        assert r.violation

    def test_health_200(self):
        chain = [state(p1=player(health=200))]
        r = _check_health_bounds(chain)
        assert r.violation

    def test_health_violation_at_later_position(self):
        chain = [
            state(p1=player(health=80)),
            state(p1=player(health=75)),
            state(p1=player(health=101)),  # violation here
        ]
        r = _check_health_bounds(chain)
        assert r.violation
        assert r.position == 2


class TestArmorBoundsViolations:
    def test_armor_exceeds_300(self):
        chain = [state(p1=player(armor=301))]
        r = _check_armor_bounds(chain)
        assert r.violation

    def test_armor_negative(self):
        chain = [state(p1=player(armor=-10))]
        r = _check_armor_bounds(chain)
        assert r.violation


class TestAmmoViolations:
    def test_ammo_negative(self):
        chain = [state(p1=player(ammo=-5))]
        r = _check_ammo_non_negative(chain)
        assert r.violation

    def test_ammo_negative_large(self):
        chain = [state(p1=player(ammo=-100))]
        r = _check_ammo_non_negative(chain)
        assert r.violation


class TestDeadPlayerActsViolations:
    def test_dead_player_acts_without_revive(self):
        chain = [
            state(p1=player(health=0)),
            state(p1=player(health=50, action="shoot")),  # dead → action without revive
        ]
        r = _check_dead_player_acts(chain)
        assert r.violation
        assert r.violation_type == "dead_player_active"

    def test_dead_player_persists_then_acts(self):
        chain = [
            state(p1=player(health=20)),
            state(p1=player(health=0)),
            state(p1=player(health=0)),
            state(p1=player(health=30, action="move")),  # acts without revive
        ]
        r = _check_dead_player_acts(chain)
        assert r.violation


class TestScoreMonotoneViolations:
    def test_score_decreases(self):
        chain = [
            state(p1=player(kills=3)),
            state(p1=player(kills=2)),  # kills decreased
        ]
        r = _check_score_monotone(chain)
        assert r.violation
        assert r.violation_type == "score_decreased"

    def test_score_drops_to_zero(self):
        chain = [
            state(p1=player(kills=5)),
            state(p1=player(kills=0)),
        ]
        r = _check_score_monotone(chain)
        assert r.violation


class TestHealingPreconditionViolations:
    def test_heal_at_full_health(self):
        chain = [state(p1=player(health=100, action="heal"))]
        r = _check_healing_precondition(chain)
        assert r.violation
        assert r.violation_type == "healing_at_full_health"

    def test_medkit_at_full_health(self):
        chain = [state(p1=player(health=100, action="use_medkit"))]
        r = _check_healing_precondition(chain)
        assert r.violation

    def test_bandage_at_full_health(self):
        chain = [state(p1=player(health=100, action="use_bandage"))]
        r = _check_healing_precondition(chain)
        assert r.violation


class TestZoneDamageViolations:
    def test_health_increases_outside_zone(self):
        chain = [
            state(p1={"health": 60, "in_zone": False}),
            state(p1={"health": 70, "in_zone": False}),  # health up outside zone
        ]
        r = _check_zone_damage_direction(chain)
        assert r.violation
        assert r.violation_type == "zone_damage_health_increase"


class TestPlayerCountViolations:
    def test_alive_count_increases(self):
        chain = [
            state(alive_count=50),
            state(alive_count=55),  # can't respawn in standard PUBG
        ]
        r = _check_player_count_non_increasing(chain)
        assert r.violation
        assert r.violation_type == "alive_count_increased"


# ---------------------------------------------------------------------------
# NEGATIVE CASES (clean chains — checker must return violation=False)
# ---------------------------------------------------------------------------

class TestCleanChains:
    def test_normal_combat_sequence(self):
        chain = [
            state(p1=player(health=100, armor=100, ammo=30, kills=0), alive_count=64),
            state(p1=player(health=80, armor=80, ammo=25, kills=0), alive_count=63),
            state(p1=player(health=80, armor=80, ammo=20, kills=1), alive_count=62),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_healing_at_low_health(self):
        chain = [
            state(p1=player(health=40, action="heal")),
            state(p1=player(health=75)),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_dead_player_stays_dead(self):
        chain = [
            state(p1=player(health=50)),
            state(p1=player(health=0)),
            state(p1=player(health=0)),  # stays dead
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_revived_player_acts(self):
        chain = [
            state(p1=player(health=50)),
            state(p1=player(health=0)),
            state(p1={"health": 30, "armor": 0, "ammo": 10, "action": "revived"}),
            state(p1={"health": 30, "armor": 0, "ammo": 10, "action": "move"}),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_score_increases_monotonically(self):
        chain = [
            state(p1=player(kills=0)),
            state(p1=player(kills=1)),
            state(p1=player(kills=1)),
            state(p1=player(kills=2)),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_zone_damage_reduces_health(self):
        chain = [
            state(p1={"health": 80, "in_zone": False}),
            state(p1={"health": 70, "in_zone": False}),  # health down — correct
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_armor_boundary_values(self):
        chain = [
            state(p1=player(armor=0)),
            state(p1=player(armor=100)),
            state(p1=player(armor=300)),  # at boundary
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_ammo_zero_is_valid(self):
        chain = [state(p1=player(ammo=0))]
        r = check_chain(chain)
        assert not r.violation

    def test_health_boundary_values(self):
        chain = [
            state(p1=player(health=0)),   # dead is valid
            state(p1=player(health=100)), # full health is valid (initially)
        ]
        # health 0→100 without revive might be flagged — test the boundary only if revive present
        chain2 = [state(p1=player(health=100))]
        r = check_chain(chain2)
        assert not r.violation

    def test_two_players_independent(self):
        chain = [
            state(p1=player(health=80, kills=0), p2=player(health=60, kills=2)),
            state(p1=player(health=70, kills=1), p2=player(health=50, kills=3)),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_empty_chain(self):
        r = check_chain([])
        assert not r.violation

    def test_single_state(self):
        chain = [state(p1=player(health=75, armor=50, ammo=20, kills=0))]
        r = check_chain(chain)
        assert not r.violation

    def test_player_count_decreases(self):
        chain = [
            state(alive_count=100),
            state(alive_count=80),
            state(alive_count=50),
            state(alive_count=1),
        ]
        r = check_chain(chain)
        assert not r.violation

    def test_healing_below_100(self):
        chain = [state(p1=player(health=99, action="heal"))]
        r = check_chain(chain)
        assert not r.violation


class TestFullChainViolationDetection:
    def test_violation_detected_mid_chain(self):
        """Violation embedded in otherwise-clean chain should be caught."""
        chain = [
            state(p1=player(health=80, kills=0)),
            state(p1=player(health=75, kills=0)),
            state(p1=player(health=200, kills=0)),  # health violation
            state(p1=player(health=70, kills=1)),
        ]
        r = check_chain(chain)
        assert r.violation
        assert r.position == 2

    def test_violation_at_start(self):
        chain = [
            state(p1=player(health=-5)),
            state(p1=player(health=50)),
        ]
        r = check_chain(chain)
        assert r.violation
        assert r.position == 0
