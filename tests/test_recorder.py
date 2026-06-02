"""Tests for BehavioralCsvWriter and manifest writers."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mid_det.recorder import (
    BEHAVIORAL_COLUMNS,
    BehavioralCsvWriter,
    TrialRecord,
    write_ratings_manifest,
)


@dataclass
class _FakeScreenDiag:
    gl_vendor: str = "TestVendor"
    gl_renderer: str = "TestRenderer"
    win_type: str = "pyglet"
    pyglet_version: str = "2.0"
    platform_str: str = "test"
    calib_median_ms: float = 16.7
    calib_p99_ms: float = 17.0
    calib_max_ms: float = 18.0
    calib_n: int = 120


def test_ratings_manifest_written(tmp_path: Path):
    write_ratings_manifest(
        run_dir=tmp_path,
        subject_id="S1",
        show_instructions=True,
        session_time=datetime(2026, 6, 2, 14, 30, 0),
        screen_diag=_FakeScreenDiag(),
        win_res=[1920, 1080],
        n_cues=6,
        scale_points=7,
    )
    with open(tmp_path / "manifest.json") as f:
        m = json.load(f)
    assert m["task"] == "cue-ratings"
    assert m["subject_id"] == "S1"
    assert m["n_cues"] == 6
    assert m["scale_points"] == 7
    assert m["display"]["resolution"] == [1920, 1080]
    assert m["display"]["gl_renderer"] == "TestRenderer"
    assert "system" in m and "psychopy_version" in m["system"]
    # Self-paced survey: no scanner/frame-timing fields.
    assert "study_params" not in m
    assert "frame_rate_hz" not in m


def test_behavioral_csv_roundtrip(tmp_path: Path):
    path = tmp_path / "b.csv"
    w = BehavioralCsvWriter(path)
    rec = TrialRecord(
        trial_n=1, trial_type=6, polarity="gain", magnitude=5,
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
