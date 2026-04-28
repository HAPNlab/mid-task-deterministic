"""
Adaptive staircase tests — all cases derived from MATLAB PresentTarget.m.

Call order mirrors the MATLAB code:
  next_target_dur_s()  →  run trial  →  record_outcome()
"""
from __future__ import annotations

import pytest

from mid_det import config
from mid_det.calibration import CalibrationState


# ── helpers ──────────────────────────────────────────────────────────────────

def _run_cue(
    cal: CalibrationState,
    valence: str,
    magnitude: int,
    outcomes: list[bool],
) -> list[float]:
    """Drive CalibrationState through scripted outcomes; return window per trial."""
    windows = []
    for hit in outcomes:
        windows.append(cal.next_target_dur_s(valence, magnitude))
        cal.record_outcome(valence, magnitude, hit)
    return windows


# ── no-adapt warmup period ────────────────────────────────────────────────────

def test_first_trial_uses_base_rt():
    cal = CalibrationState(base_rt_s=0.265)
    assert cal.next_target_dur_s("gain", 5) == pytest.approx(0.265)


def test_no_adapt_first_three_trials():
    """
    PresentTarget.m: elseif length(prior_wins) > 2 — adaptation gate.
    Trials 1-3 of any cue return base_rt regardless of outcomes.
    """
    base = 0.265
    cal = CalibrationState(base_rt_s=base)
    windows = _run_cue(cal, "gain", 5, [True, False, True])
    assert windows == pytest.approx([base, base, base])


# ── adaptation direction ──────────────────────────────────────────────────────

def test_shrinks_after_three_wins():
    """
    ratio = 3/3 = 1.0 > 0.66  →  4th trial shrinks by rt_change.
    5th trial: ratio = 4/4 = 1.0 > 0.66  →  shrinks again (compounding).
    """
    base = 0.265
    cal = CalibrationState(base_rt_s=base)
    windows = _run_cue(cal, "gain", 5, [True, True, True, True, True])
    assert windows[0] == pytest.approx(base)
    assert windows[1] == pytest.approx(base)
    assert windows[2] == pytest.approx(base)
    assert windows[3] == pytest.approx(base - 0.020)
    assert windows[4] == pytest.approx(base - 0.040)


def test_grows_after_three_misses():
    """ratio = 0/3 = 0.0  ≤  0.66  →  4th trial grows by rt_change."""
    base = 0.265
    cal = CalibrationState(base_rt_s=base)
    windows = _run_cue(cal, "loss", 1, [False, False, False, False])
    assert windows[3] == pytest.approx(base + 0.020)


# ── ratio boundary ────────────────────────────────────────────────────────────

def test_ratio_boundary_shrink_and_grow():
    """
    PresentTarget.m: if ratio > 0.66 → decrement; elseif ratio <= 0.66 → increment.
    2W/1L = 0.667 > 0.66  →  shrinks.
    1W/2L = 0.333 ≤ 0.66  →  grows.
    """
    base = 0.265

    cal = CalibrationState(base_rt_s=base)
    wins = _run_cue(cal, "gain", 5, [True, True, False, True])
    assert wins[3] == pytest.approx(base - 0.020)

    cal = CalibrationState(base_rt_s=base)
    wins = _run_cue(cal, "gain", 5, [True, False, False, True])
    assert wins[3] == pytest.approx(base + 0.020)


def test_ratio_exactly_066_grows():
    """
    Condition is strictly > 0.66; ratio == 0.66 must grow, not shrink.
    33 wins + 17 losses = 50 trials  →  ratio = 33/50 = 0.66 exactly.
    """
    base = 0.300
    cal = CalibrationState(base_rt_s=base)
    _run_cue(cal, "gain", 1, [True] * 33 + [False] * 17)
    w_next = cal.next_target_dur_s("gain", 1)
    w_prev = cal._calibrations[("gain", 1)][-2]
    assert w_next == pytest.approx(w_prev + 0.020)


# ── per-cue independence ──────────────────────────────────────────────────────

def test_cues_are_independent():
    """
    MATLAB uses separate var.calibrations{1..6} per cue type.
    Adaptation on one cue must not affect another.
    """
    base = 0.265
    cal = CalibrationState(base_rt_s=base)
    _run_cue(cal, "gain", 5, [True, True, True])
    # loss/1 unseen → still base_rt
    assert cal.next_target_dur_s("loss", 1) == pytest.approx(base)
    # gain/5 on 4th trial → shrink
    assert cal.next_target_dur_s("gain", 5) == pytest.approx(base - 0.020)


# ── early press treatment ─────────────────────────────────────────────────────

def test_early_press_counts_as_loss_for_calibration():
    """
    PresentTarget.m line 108: early press sets prior_wins entry to 0 — identical
    to a regular miss.  CalibrationState must treat hit=False the same way.
    """
    base = 0.265
    cal_early = CalibrationState(base_rt_s=base)
    cal_miss  = CalibrationState(base_rt_s=base)
    wins_early = _run_cue(cal_early, "gain", 5, [False, False, False, False])
    wins_miss  = _run_cue(cal_miss,  "gain", 5, [False, False, False, False])
    assert wins_early == pytest.approx(wins_miss)
