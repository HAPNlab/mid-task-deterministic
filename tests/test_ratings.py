"""Tests for the cue-ratings survey core logic — traced to MATLAB RunRatings.m /
ParseData.m. PsychoPy-free (imports only mid_det.ratings.core)."""
from __future__ import annotations

import csv

import pytest

from mid_det import config
from mid_det.ratings import core


def test_cue_order():
    # MATLAB var.cues = [1..6]: loss 0/1/5 then gain 0/1/5.
    assert [c.idx for c in core.RATING_CUES] == [1, 2, 3, 4, 5, 6]
    assert [(c.polarity, c.magnitude) for c in core.RATING_CUES] == [
        ("loss", 0), ("loss", 1), ("loss", 5),
        ("gain", 0), ("gain", 1), ("gain", 5),
    ]


def test_cue_polarity_magnitude_consistent_with_config():
    # square = loss, circle = gain; magnitude 0/1/5.
    for c in core.RATING_CUES:
        shape = config.POLARITY_SHAPE[c.polarity]
        assert shape in ("circle", "square")
        if c.polarity == "loss":
            assert shape == "square"
        else:
            assert shape == "circle"
        assert c.magnitude in config.MAGNITUDES


def test_seven_point_scale():
    assert core.N_ELS == 7
    assert len(core.VALENCE_COLORS_255) == 7
    assert len(core.AROUSAL_COLORS_255) == 7


def test_start_positions_match_matlab():
    # MATLAB: valence c.slidepos = round(numEls/2) = 4; arousal c.slidepos = 1.
    assert core.START_SLIDEPOS["valence"] == 4
    assert core.START_SLIDEPOS["arousal"] == 1


def test_slider_clamping():
    # Moving left at the floor stays at 1; right at the ceiling stays at N_ELS.
    assert core.clamp_slider(1, -1) == 1
    assert core.clamp_slider(7, +1) == 7
    assert core.clamp_slider(4, +1) == 5
    assert core.clamp_slider(4, -1) == 3


def test_csv_header_and_rows():
    results = [
        {"polarity": "loss", "magnitude": 0, "arousal": 3, "valence": 2},
        {"polarity": "gain", "magnitude": 5, "arousal": 7, "valence": 6},
    ]
    rows = core.build_csv_rows(results)
    assert rows[0] == ["polarity", "magnitude", "arousal", "valence"]
    assert rows[1] == ["loss", "0", "3", "2"]
    assert rows[2] == ["gain", "5", "7", "6"]


def test_write_ratings_csv(tmp_path):
    results = [
        {"polarity": c.polarity, "magnitude": c.magnitude, "arousal": 4, "valence": 4}
        for c in core.RATING_CUES
    ]
    out = tmp_path / "S1_ratings.csv"
    core.write_ratings_csv(out, results)

    with open(out, newline="") as f:
        read = list(csv.reader(f))
    assert read[0] == ["polarity", "magnitude", "arousal", "valence"]
    assert len(read) == 1 + len(core.RATING_CUES)
    assert [(r[0], int(r[1])) for r in read[1:]] == [
        (c.polarity, c.magnitude) for c in core.RATING_CUES
    ]


def test_ratings_in_valid_range():
    for r in range(1, core.N_ELS + 1):
        assert 1 <= core.clamp_slider(r, 0) <= core.N_ELS
