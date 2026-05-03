"""Tests for D-0.5 structural feature extraction."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tier0.d_0_5_output_structure import extract_structural_features


class TestExtractStructuralFeatures:
    def test_refusal_marker_detected(self):
        resp = "I cannot assist with this request."
        feats = extract_structural_features(resp)
        assert feats["refusal_present"] == 1.0

    def test_hedge_marker_detected(self):
        resp = "Perhaps this might be a violation, though it's unclear."
        feats = extract_structural_features(resp)
        assert feats["hedge_present"] == 1.0

    def test_self_reference_detected(self):
        resp = "According to the rules stated above, this is a violation."
        feats = extract_structural_features(resp)
        assert feats["self_reference_present"] == 1.0

    def test_confidence_marker_detected(self):
        resp = "This is definitely a violation of the constraints."
        feats = extract_structural_features(resp)
        assert feats["confidence_present"] == 1.0

    def test_clean_response_no_markers(self):
        resp = "Yes, this is a violation."
        feats = extract_structural_features(resp)
        assert feats["refusal_present"] == 0.0
        assert feats["hedge_present"] == 0.0
        assert feats["self_reference_present"] == 0.0

    def test_token_count(self):
        resp = "This is five words here"
        feats = extract_structural_features(resp)
        assert feats["token_count"] == 5

    def test_empty_string(self):
        feats = extract_structural_features("")
        assert feats["token_count"] == 0
        assert feats["refusal_present"] == 0.0

    def test_returns_dict(self):
        feats = extract_structural_features("some response text")
        assert isinstance(feats, dict)
        assert "token_count" in feats
        assert "refusal_present" in feats
        assert "hedge_present" in feats
        assert "self_reference_present" in feats
        assert "confidence_present" in feats
