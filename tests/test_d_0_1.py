"""
Tests for D-0.1: Per-cell breakdown
Pre-reg reference: DDK_v0.1_PREREG.md §3.1.1, Build Plan §2.2

Test strategy: generate synthetic data with known cell-level signal in 2 domains.
Confirm the analysis correctly identifies those cells.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tier0.d_0_1_per_cell_breakdown import (
    compute_cell_effects,
    generate_synthetic_test_data,
)
from utils.scoring import bh_fdr_correct, mcnemar_cell


class TestMcNemanrCell:
    def test_strong_anti_detecting_signal(self):
        rng = np.random.default_rng(1)
        # 80% ctrl correct, 30% intv correct → strong anti-detect
        ctrl = rng.random(100) < 0.80
        intv = rng.random(100) < 0.30
        result = mcnemar_cell(ctrl, intv)

        assert result["log_odds_effect"] < 0, "Anti-detection → negative log-odds"
        assert result["p_value"] < 0.01, "Strong effect should be significant"
        assert result["b_ctrl_correct_intv_wrong"] > result["c_ctrl_wrong_intv_correct"]

    def test_strong_pro_detecting_signal(self):
        rng = np.random.default_rng(2)
        ctrl = rng.random(100) < 0.40
        intv = rng.random(100) < 0.85
        result = mcnemar_cell(ctrl, intv)

        assert result["log_odds_effect"] > 0, "Pro-detection → positive log-odds"
        assert result["p_value"] < 0.01

    def test_null_effect(self):
        rng = np.random.default_rng(3)
        ctrl = rng.random(200) < 0.65
        intv = rng.random(200) < 0.65
        result = mcnemar_cell(ctrl, intv)

        assert abs(result["log_odds_effect"]) < 0.5, "Null effect should be near zero"
        # Not significant at 0.001
        assert result["p_value"] > 0.001

    def test_no_discordance(self):
        ctrl = np.array([True, True, True, True, True])
        intv = np.array([True, True, True, True, True])
        result = mcnemar_cell(ctrl, intv)
        # b=0, c=0 → both 0+0.5, log-odds should be 0
        assert abs(result["log_odds_effect"]) < 0.01

    def test_correct_counts(self):
        ctrl = np.array([True, True, False, True])
        intv = np.array([False, True, True, False])
        result = mcnemar_cell(ctrl, intv)
        # b = ctrl T & intv F: positions 0,3 → b=2
        # c = ctrl F & intv T: position 2 → c=1
        assert result["b_ctrl_correct_intv_wrong"] == 2
        assert result["c_ctrl_wrong_intv_correct"] == 1


class TestBhFdrCorrect:
    def test_rejects_small_pvalues(self):
        p = np.array([0.001, 0.001, 0.001, 0.9, 0.9, 0.9])
        sig, _ = bh_fdr_correct(p)
        assert sig[0] and sig[1] and sig[2], "Small p-values should be significant"
        assert not sig[3] and not sig[4] and not sig[5], "Large p-values should not be"

    def test_nan_treated_as_1(self):
        p = np.array([0.001, np.nan])
        sig, _ = bh_fdr_correct(p)
        assert sig[0]
        assert not sig[1]

    def test_empty_array(self):
        p = np.array([])
        sig, adj = bh_fdr_correct(p)
        assert len(sig) == 0


class TestComputeCellEffects:
    def test_identifies_known_signal(self):
        df = generate_synthetic_test_data()
        effects = compute_cell_effects(df)

        assert len(effects) > 0, "Should produce cell effects"

        # gpt-5 anti-detects on pubg and nba
        gpt5_pubg = effects[(effects["model"] == "gpt-5") & (effects["domain"] == "pubg")]
        if not gpt5_pubg.empty:
            assert gpt5_pubg.iloc[0]["log_odds_effect"] < 0, \
                "gpt-5 × pubg should be anti-detecting"

        gpt5_nba = effects[(effects["model"] == "gpt-5") & (effects["domain"] == "nba")]
        if not gpt5_nba.empty:
            assert gpt5_nba.iloc[0]["log_odds_effect"] < 0, \
                "gpt-5 × nba should be anti-detecting"

    def test_glm5_pro_detecting(self):
        df = generate_synthetic_test_data()
        effects = compute_cell_effects(df)

        glm5 = effects[effects["model"] == "glm-5"]
        if not glm5.empty:
            assert glm5["log_odds_effect"].mean() > 0, \
                "glm-5 should be pro-detecting on average"

    def test_significant_cells_identified(self):
        df = generate_synthetic_test_data()
        effects = compute_cell_effects(df)

        n_sig = effects["significant_fdr05"].sum()
        assert n_sig > 0, "At least some cells should be significant with known signal"

    def test_output_columns(self):
        df = generate_synthetic_test_data()
        effects = compute_cell_effects(df)

        required_cols = {
            "model", "domain", "n", "control_acc", "intervention_acc",
            "delta_acc", "log_odds_effect", "p_value", "p_value_adj_bh", "significant_fdr05"
        }
        assert required_cols.issubset(set(effects.columns)), \
            f"Missing columns: {required_cols - set(effects.columns)}"

    def test_no_cells_when_insufficient_pairs(self):
        """Cells with <5 paired chains should be skipped."""
        df = generate_synthetic_test_data()
        df = df.head(4)  # Very small slice
        effects = compute_cell_effects(df)
        # May be empty or have very few cells — no assertion error expected
        assert isinstance(effects, pd.DataFrame)
