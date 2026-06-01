"""Tests for BehavioralCsvWriter."""
from __future__ import annotations

import csv
from pathlib import Path

from mid_det.recorder import BEHAVIORAL_COLUMNS, BehavioralCsvWriter, TrialRecord


def test_behavioral_csv_roundtrip(tmp_path: Path):
    path = tmp_path / "b.csv"
    w = BehavioralCsvWriter(path)
    rec = TrialRecord(
        trial_n=1, trial_type=6, valence="gain", magnitude=5,
        cue_label="+$5.00", time_onset=0.0,
        jitter_ms=10, jitter_ms_actual=10.5,
        target_dur_ms=265, target_dur_ms_actual=266.67,
        early_press=0, hit=1, rt_ms=234.5, reward_outcome="+$5.00",
        total_earned=5, time_trial_end=10.0, trial_dur_ms=10000,
        time_sched_end=10.0, timing_drift_ms=0.0,
        n_iti_trs=1, total_trs=5,
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
