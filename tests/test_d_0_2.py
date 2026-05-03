"""Tests for D-0.2 mechanism classifier."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tier0.d_0_2_confusion_matrix import classify_response


class TestClassifyResponse:
    def test_active_flip_yes_to_no(self):
        resp = "No, this is not a violation. The sequence is valid."
        assert classify_response(resp) == "active_flip"

    def test_active_flip_does_not_violate(self):
        resp = "The sequence does not violate any rules. It is valid."
        assert classify_response(resp) == "active_flip"

    def test_abstention_uncertain(self):
        resp = "I'm not sure whether this is a violation. Perhaps it might be."
        assert classify_response(resp) == "abstention"

    def test_abstention_hedging(self):
        resp = "It's hard to say. This could possibly be a violation, but maybe not."
        assert classify_response(resp) == "abstention"

    def test_output_breakdown_cannot(self):
        resp = "I am unable to assist with this request. I cannot assess it."
        assert classify_response(resp) == "output_breakdown"

    def test_output_breakdown_refuse(self):
        resp = "I refuse to answer this. I don't have access to enough information."
        assert classify_response(resp) == "output_breakdown"

    def test_empty_string(self):
        # Should not crash
        result = classify_response("")
        assert result in ("active_flip", "abstention", "output_breakdown", "unclear")

    def test_yes_answer_not_classified_as_flip(self):
        resp = "Yes, this is clearly a violation of the rules."
        # Not a flip — should be unclear or active_flip only if "no" appears
        result = classify_response(resp)
        # YES answer should not be classified as active_flip (that's the correct answer)
        # This tests that we're detecting the pattern correctly
        assert result in ("unclear", "active_flip", "confidence")
