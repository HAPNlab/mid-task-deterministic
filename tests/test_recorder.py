"""Tests for BehavioralCsvWriter and manifest writers."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest

from mid_det.recorder import (
    BEHAVIORAL_COLUMNS,
    LEGACY_MID_COLUMNS,
    BehavioralCsvWriter,
    LegacyMidCsvWriter,
    TrialRecord,
    _num2str,
    write_ratings_manifest,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.0, "0"),            # zero
        (0.16667, "0.16667"),  # < 1 -> 5 sig figs
        (1 / 3, "0.33333"),    # < 1 -> 5 sig figs (rounded)
        (1.0, "1"),            # whole value collapses
        (-1, "-1"),            # integer miss code
        (-2, "-2"),            # early-press code
        (0.4, "0.4"),          # short decimal kept short
        (12.013308, "12.0133"),  # magnitude > 1 -> 6 sig figs
        (-0.00011858, "-0.00011858"),  # tiny drift -> 5 sig figs, no sci (exp -4)
        (-7.83e-05, "-7.83e-05"),      # exp < -4 -> scientific, like num2str
    ],
)
def test_num2str_matches_matlab(value, expected):
    assert _num2str(value) == expected


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


def _legacy_record(**overrides) -> TrialRecord:
    base = dict(
        trial_n=1, trial_type=4, polarity="gain", magnitude=0,
        cue_label="+$0.00", time_onset=12.0003,
        jitter_ms=10, jitter_ms_actual=10.5,
        target_dur_ms=400, target_dur_ms_actual="",
        early_press=0, hit=0, rt_ms="", reward_outcome="$0.00",
        total_earned=0, time_trial_end=26.0, trial_dur_ms=14000,
        time_sched_end=26.0, timing_drift_ms=-0.12,
        n_iti_trs=3, total_trs=7,
        subject_id="X", run_n="1", pulse_ct=0,
    )
    base.update(overrides)
    return TrialRecord(**base)


def test_legacy_mid_per_tr_rows_and_header(tmp_path: Path):
    path = tmp_path / "1_b1.csv"
    w = LegacyMidCsvWriter(path)
    w.append(_legacy_record(total_trs=7))   # 7 TR rows
    w.append(_legacy_record(trial_n=2, total_trs=5, n_iti_trs=1))  # 5 TR rows
    w.close()

    with open(path) as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == LEGACY_MID_COLUMNS
        rows = list(reader)
    assert len(rows) == 7 + 5
    assert [r["TR"] for r in rows[:7]] == [str(i) for i in range(1, 8)]
    assert all(r["trial"] == "1" for r in rows[:7])
    assert [r["TR"] for r in rows[7:]] == [str(i) for i in range(1, 6)]


def test_legacy_mid_formatting_and_winpercents(tmp_path: Path):
    # Formats traced to MATLAB PresentCue.m / PresentFeedback.m / PartialParseData.m
    # / PresentTarget.m.
    path = tmp_path / "leg.csv"
    w = LegacyMidCsvWriter(path)
    # gain $0 miss (type 4): cue +$0, gain $0 (gain miss), total $0.00
    w.append(_legacy_record(trial_n=1, trial_type=4, polarity="gain", magnitude=0,
                            hit=0, early_press=0, total_earned=0,
                            target_dur_ms=400, rt_ms="", timing_drift_ms=-0.12,
                            n_iti_trs=3, total_trs=7))
    # loss $1 miss (type 2): cue -$1, gain -$1, running total -1 -> "$-1.00"
    w.append(_legacy_record(trial_n=2, trial_type=2, polarity="loss", magnitude=1,
                            hit=0, early_press=0, total_earned=-1,
                            target_dur_ms=400, rt_ms="", n_iti_trs=3, total_trs=7))
    # loss $1 hit (type 2): cue -$1, gain $0 (loss avoided), total unchanged, rt set
    w.append(_legacy_record(trial_n=3, trial_type=2, polarity="loss", magnitude=1,
                            hit=1, early_press=0, total_earned=-1,
                            target_dur_ms=420, rt_ms=226.54, n_iti_trs=3, total_trs=7))
    w.close()

    with open(path) as f:
        rows = list(csv.DictReader(f))

    t1, t2, t3 = rows[0], rows[7], rows[14]
    # target_ms / rt / drift are in seconds, formatted via MATLAB-style num2str.
    assert t1["target_ms"] == "0.4"
    assert t1["rt"] == "-1"          # miss
    assert t1["cue_value"] == "+$0"
    assert t1["trial_gain"] == "$0"  # gain trial, missed
    assert t1["total"] == "$0.00"
    assert t1["iti"] == "6"
    assert t1["drift"] == "-0.00012"  # -0.12 ms, num2str 5 sig figs
    assert t1["total_winpercent"] == "0"   # num2str: 0.0 -> "0"
    assert t1["binned_winpercent"] == "0"

    # loss $1 miss: incurs the loss
    assert t2["cue_value"] == "-$1"
    assert t2["trial_gain"] == "-$1"
    assert t2["total"] == "$-1.00"
    # loss $1 hit: loss avoided, rt recorded
    assert t3["cue_value"] == "-$1"
    assert t3["trial_gain"] == "$0"
    assert t3["total"] == "$-1.00"
    assert t3["rt"] == "0.22654"
    assert t3["target_ms"] == "0.42"
    # win%: after 3 trials, 1 hit overall -> 1/3; type-2 has 2 trials, 1 hit -> 1/2.
    # num2str renders 1/3 to 5 sig figs ("0.33333").
    assert t3["total_winpercent"] == "0.33333"
    assert t3["binned_winpercent"] == "0.5"


def test_legacy_mid_early_press_rt(tmp_path: Path):
    # MATLAB encodes an early (front-buffer) press as rt = -2, distinct from a
    # miss (-1); both score hit = 0.
    path = tmp_path / "early.csv"
    w = LegacyMidCsvWriter(path)
    w.append(_legacy_record(hit=0, early_press=1, rt_ms="", total_trs=5))
    w.close()
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["rt"] == "-2"
    assert rows[0]["hit"] == "0"


def test_legacy_mid_block2_trial_offset(tmp_path: Path):
    # MATLAB PartialParseData.m: block-2 trials are numbered from 43 (offset 42).
    path = tmp_path / "b2.csv"
    w = LegacyMidCsvWriter(path, trial_offset=42)
    w.append(_legacy_record(trial_n=1, total_trs=5))
    w.close()
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert all(r["trial"] == "43" for r in rows)
