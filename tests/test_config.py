"""Tests for config constants — all values traced to MATLAB main.m / PresentTarget.m."""
from __future__ import annotations

import pytest

from mid_det import config


def test_trial_type_map_covers_all_conditions():
    # 6 cue types: 2 valences × 3 magnitudes (matches MATLAB var.cues 1..6).
    assert len(config.TRIAL_TYPE_MAP) == 6
    assert set(config.TRIAL_TYPE_MAP.values()) == set(range(1, 7))
    assert config.TRIAL_TYPE_MAP[("loss", 0)] == 1
    assert config.TRIAL_TYPE_MAP[("gain", 5)] == 6


def test_cue_label_format():
    # Labels include .00 suffix to match MATLAB var.usedecimals = 1.
    assert config.cue_label("gain", 5) == "+$5.00"
    assert config.cue_label("gain", 0) == "+$0.00"
    assert config.cue_label("loss", 1) == "-$1.00"
    assert config.cue_label("loss", 0) == "-$0.00"


def test_jitter_range_matches_matlab():
    # PresentTarget.m: frontbuffer = 0.25 + rand()*0.75  →  [0.25, 1.0)
    assert config.JITTER_MIN_S == pytest.approx(0.25)
    assert config.JITTER_MAX_S == pytest.approx(1.0)
    assert config.JITTER_MIN_S < config.JITTER_MAX_S


def test_phase_durations_match_matlab():
    # MATLAB: each of cue / fixation / target-window / feedback = 2.0 s (1 TR).
    # Total non-ITI trial time = 8.0 s = 4 TRs  (main.m comment line 26).
    phases = ["cue", "fixation", "response", "outcome"]
    for p in phases:
        assert config.STUDY_TIMES_S[p] == pytest.approx(2.0), (
            f"Phase '{p}' should be 2.0 s to match MATLAB"
        )
    assert sum(config.STUDY_TIMES_S[p] for p in phases) == pytest.approx(8.0)


def test_leadin_leadout_match_matlab():
    # main.m: var.leadin = 12.0, var.leadout = 8.0 (scanned blocks).
    assert config.INITIAL_FIX_DUR_S == pytest.approx(12.0)
    assert config.CLOSING_FIX_DUR_S == pytest.approx(8.0)


def test_practice_leadin_leadout_match_matlab():
    # main.m lines 154-155: practice sets leadin=2, leadout=0.
    assert config.PRACTICE_INITIAL_FIX_DUR_S == pytest.approx(2.0)
    assert config.PRACTICE_CLOSING_FIX_DUR_S == pytest.approx(0.0)


def test_calibration_constants_match_matlab():
    # PresentTarget.m: var.rt_change = .020, WIN_RATIO_THRESHOLD = 0.66,
    # adapt begins once length(prior_wins) > 2  →  MIN_TRIALS_FOR_ADAPT = 3.
    assert config.RT_CHANGE_S == pytest.approx(0.020)
    assert config.WIN_RATIO_THRESHOLD == pytest.approx(0.66)
    assert config.MIN_TRIALS_FOR_ADAPT == 3
