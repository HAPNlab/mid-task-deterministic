"""
Reward computation tests — all cases derived from MATLAB PresentFeedback.m.

PresentFeedback.m switch statement maps (cue_type, won) → (valuestr, value):
  cue 1 (loss $0):  hit → '$0',   miss → '-$0'   (Δ = 0 either way)
  cue 2 (loss $1):  hit → '$0',   miss → '-$1'   (Δ = 0 or -1)
  cue 3 (loss $5):  hit → '$0',   miss → '-$5'   (Δ = 0 or -5)
  cue 4 (gain $0):  hit → '+$0',  miss → '$0'    (Δ = 0 either way)
  cue 5 (gain $1):  hit → '+$1',  miss → '$0'    (Δ = +1 or 0)
  cue 6 (gain $5):  hit → '+$5',  miss → '$0'    (Δ = +5 or 0)

Labels include '.00' suffix (var.usedecimals = 1 in main.m).
"""
from __future__ import annotations

import pytest

from mid_det.task.trial import _compute_reward


@pytest.mark.parametrize(
    "hit,polarity,mag,expected_label,expected_delta",
    [
        # Gain (circle) cues: hit → earn magnitude, miss → $0
        (True,  "gain", 5, "+$5.00", +5),
        (True,  "gain", 1, "+$1.00", +1),
        (True,  "gain", 0, "+$0.00",  0),
        (False, "gain", 5,  "$0.00",  0),
        (False, "gain", 1,  "$0.00",  0),
        (False, "gain", 0,  "$0.00",  0),
        # Loss (square) cues: hit → avoid loss ($0), miss → lose magnitude
        (True,  "loss", 5,  "$0.00",  0),
        (True,  "loss", 1,  "$0.00",  0),
        (True,  "loss", 0,  "$0.00",  0),
        (False, "loss", 5, "-$5.00", -5),
        (False, "loss", 1, "-$1.00", -1),
        (False, "loss", 0, "-$0.00",  0),
    ],
)
def test_all_12_conditions(hit, polarity, mag, expected_label, expected_delta):
    """All 12 (polarity × magnitude × hit/miss) cases from PresentFeedback.m."""
    label, new_total = _compute_reward(hit, polarity, mag, total_earned=0)
    assert label == expected_label
    assert new_total == expected_delta


def test_running_total_accumulates():
    """
    PresentFeedback.m: data.total = data.total + value.
    Verify the running total across a short scripted sequence.
    """
    total = 0
    steps = [
        # (hit, polarity, mag, expected_total_after)
        (True,  "gain", 5,  5),   # +$5
        (False, "gain", 5,  5),   # $0  (miss)
        (True,  "loss", 5,  5),   # $0  (avoided)
        (False, "loss", 5,  0),   # -$5
        (True,  "gain", 1,  1),   # +$1
        (False, "loss", 1,  0),   # -$1
    ]
    for hit, polarity, mag, expected in steps:
        _, total = _compute_reward(hit, polarity, mag, total)
        assert total == expected
