"""Tests for PulseCounter and BehavioralCsvWriter."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mid_det import config
from mid_det.recorder import BEHAVIORAL_COLUMNS, BehavioralCsvWriter, TrialRecord
from mid_det.scanner import PulseCounter


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


def test_behavioral_csv_roundtrip(tmp_path: Path):
    path = tmp_path / "b.csv"
    w = BehavioralCsvWriter(path)
    rec = TrialRecord(
        trial_n=1, trial_type=6, valence="gain", magnitude=5,
        cue_label="+$5.00", time_onset=0.0, jitter_ms=10, target_dur_ms=265,
        early_press=0, hit=1, rt_ms=234.5, reward_outcome="+$5.00",
        total_earned=5, time_trial_end=10.0, trial_dur_ms=10000,
        time_sched_end=10.0, timing_drift_ms=0.0, total_trs=5,
        subject_id="X", run_n="1", pulse_ct=0,
    )
    w.append(rec)
    w.close()

    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert set(rows[0].keys()) == set(BEHAVIORAL_COLUMNS)
    assert rows[0]["cue_label"] == "+$5.00"
    assert rows[0]["reward_outcome"] == "+$5.00"
