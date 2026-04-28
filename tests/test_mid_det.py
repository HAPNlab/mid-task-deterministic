"""
Smoke tests for mid_det.  Focused on the pieces that don't require a real
PsychoPy window: config invariants, sequence loading/validation, reward
computation, and PulseCounter + CsvWriter with a fake backend.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from mid_det import config
from mid_det.calibration import CalibrationState
from mid_det.recorder import BehavioralCsvWriter, BEHAVIORAL_COLUMNS, TrialRecord
from mid_det.scanner import PulseCounter
from mid_det.session import load_sequence
from mid_det.trial import _compute_reward


# ────────────────────────────────────────────────────────────────────────────
# config
# ────────────────────────────────────────────────────────────────────────────


def test_trial_type_map_covers_all_conditions():
    # 6 cue types: 2 valences × 3 magnitudes (matches MATLAB var.cues 1..6).
    assert len(config.TRIAL_TYPE_MAP) == 6
    assert set(config.TRIAL_TYPE_MAP.values()) == set(range(1, 7))
    assert config.TRIAL_TYPE_MAP[("loss", 0)] == 1
    assert config.TRIAL_TYPE_MAP[("gain", 5)] == 6


def test_calibration_constants_match_matlab():
    assert config.RT_CHANGE_S == pytest.approx(0.020)
    assert config.WIN_RATIO_THRESHOLD == pytest.approx(0.66)
    assert config.MIN_TRIALS_FOR_ADAPT == 3


def test_jitter_range_matches_matlab():
    assert config.JITTER_MIN_S == pytest.approx(0.25)
    assert config.JITTER_MAX_S == pytest.approx(1.0)
    assert config.JITTER_MIN_S < config.JITTER_MAX_S


def test_cue_label():
    assert config.cue_label("gain", 5) == "+$5"
    assert config.cue_label("gain", 0) == "+$0"
    assert config.cue_label("loss", 1) == "-$1"


# ────────────────────────────────────────────────────────────────────────────
# sequence loading
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("run_n", ["1", "2", "practice"])
def test_shipped_sequences_load(run_n):
    df = load_sequence(run_n)
    assert set(df.columns) >= {"valence", "magnitude", "n_iti"}
    assert len(df) > 0
    assert df["valence"].isin(config.VALENCES).all()
    assert df["magnitude"].isin(config.MAGNITUDES).all()


# ────────────────────────────────────────────────────────────────────────────
# reward computation
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "hit,valence,mag,expected_label,delta",
    [
        (True,  "gain", 5, "+$5", +5),
        (True,  "gain", 1, "+$1", +1),
        (True,  "gain", 0, "+$0",  0),
        (False, "gain", 5, "$0",   0),
        (True,  "loss", 5, "$0",   0),
        (False, "loss", 5, "-$5", -5),
        (False, "loss", 1, "-$1", -1),
        (False, "loss", 0, "-$0",  0),
    ],
)
def test_compute_reward(hit, valence, mag, expected_label, delta):
    label, new_total = _compute_reward(hit, valence, mag, total_earned=100)
    assert label == expected_label
    assert new_total == 100 + delta


# ────────────────────────────────────────────────────────────────────────────
# Adaptive calibration staircase
# ────────────────────────────────────────────────────────────────────────────


def test_calibration_first_trial_uses_base_rt():
    cal = CalibrationState(base_rt_s=0.265)
    assert cal.next_target_dur_s("gain", 5) == pytest.approx(0.265)


def test_calibration_no_change_for_first_three_trials():
    """MATLAB: trials 1-3 of each cue all use base_rt — no adaptation yet."""
    cal = CalibrationState(base_rt_s=0.265)
    for _ in range(3):
        d = cal.next_target_dur_s("gain", 5)
        assert d == pytest.approx(0.265)
        cal.record_outcome("gain", 5, hit=True)


def test_calibration_shrinks_when_winning():
    """3 wins → ratio=1.0 > 0.66 → 4th trial window shrinks by rt_change."""
    cal = CalibrationState(base_rt_s=0.265)
    for _ in range(3):
        cal.next_target_dur_s("gain", 5)
        cal.record_outcome("gain", 5, hit=True)
    d4 = cal.next_target_dur_s("gain", 5)
    assert d4 == pytest.approx(0.265 - config.RT_CHANGE_S)


def test_calibration_grows_when_losing():
    """3 misses → ratio=0 ≤ 0.66 → 4th trial window grows by rt_change."""
    cal = CalibrationState(base_rt_s=0.265)
    for _ in range(3):
        cal.next_target_dur_s("gain", 5)
        cal.record_outcome("gain", 5, hit=False)
    d4 = cal.next_target_dur_s("gain", 5)
    assert d4 == pytest.approx(0.265 + config.RT_CHANGE_S)


def test_calibration_independent_per_cue():
    cal = CalibrationState(base_rt_s=0.265)
    for _ in range(3):
        cal.next_target_dur_s("gain", 5)
        cal.record_outcome("gain", 5, hit=True)
    # Different cue type → still on first trial → base_rt
    d_other = cal.next_target_dur_s("loss", 1)
    assert d_other == pytest.approx(0.265)


# ────────────────────────────────────────────────────────────────────────────
# PulseCounter + fake backend
# ────────────────────────────────────────────────────────────────────────────


class FakeBackend:
    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        self._count = 0

    def read(self) -> int:
        return self._count

    def start(self) -> None:
        pass

    def advance(self, n: int) -> None:
        self._count += n


def test_pulse_counter_drain():
    be = FakeBackend()
    pc = PulseCounter(be)
    assert pc.drain() == 0
    be.advance(3)
    assert pc.drain() == 3
    assert pc.drain() == 0


# ────────────────────────────────────────────────────────────────────────────
# CSV writer
# ────────────────────────────────────────────────────────────────────────────


def test_behavioral_csv_roundtrip(tmp_path: Path):
    path = tmp_path / "b.csv"
    w = BehavioralCsvWriter(path)
    rec = TrialRecord(
        trial_n=1, trial_type=6, valence="gain", magnitude=5,
        cue_label="+$5", time_onset=0.0, jitter_ms=10, target_dur_ms=265,
        early_press=0, hit=1, rt_ms=234.5, reward_outcome="+$5", total_earned=5,
        time_trial_end=10.0, trial_dur_ms=10000, time_sched_end=10.0,
        timing_drift_ms=0.0, total_trs=5, subject_id="X", run_n="1", pulse_ct=0,
    )
    w.append(rec)
    w.close()

    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert set(rows[0].keys()) == set(BEHAVIORAL_COLUMNS)
    assert rows[0]["cue_label"] == "+$5"
    assert rows[0]["reward_outcome"] == "+$5"
