"""
Trial data records and their CSV column schemas: TrialRecord, TargetTimingRecord,
ScanPhase. Pure data — no behaviour, no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrialRecord:
    trial_n: int
    trial_type: int
    polarity: str
    magnitude: int
    cue_label: str
    time_onset: float
    jitter_ms: int
    jitter_ms_actual: float | str
    target_dur_ms: int
    target_dur_ms_actual: float | str
    early_press: int
    hit: int
    rt_ms: float | str
    reward_outcome: str
    total_earned: int
    time_trial_end: float
    trial_dur_ms: int
    time_sched_end: float
    timing_drift_ms: float
    n_iti_trs: int
    total_trs: int
    subject_id: str
    run_n: str
    pulse_ct: int


@dataclass
class TargetTimingRecord:
    trial_n: int
    target_frames_scheduled: int
    target_frames_shown: int
    target_visible_ms_scheduled: float
    target_visible_ms_measured: float | str
    late_flips_in_window: int
    longest_frame_interval_ms: float
    target_timing_ok: int


@dataclass
class ScanPhase:
    trial_n: int
    phase: str
    tr_n: int
    phase_onset_global_time: float
    phase_onset_trial_time: float
    pulse_ct: int
    phase_offset_global_time: float = 0.0
    phase_offset_trial_time: float = 0.0
    trial_type: int = 0
    polarity: str = ""
    magnitude: int = 0


BEHAVIORAL_COLUMNS: list[str] = [
    "trial_n", "trial_type", "polarity", "magnitude", "cue_label",
    "time_onset", "jitter_ms", "jitter_ms_actual",
    "target_dur_ms", "target_dur_ms_actual", "early_press", "hit", "rt_ms",
    "reward_outcome", "total_earned", "time_trial_end", "trial_dur_ms",
    "time_sched_end", "timing_drift_ms", "n_iti_trs", "total_trs",
    "subject_id", "run_n", "pulse_ct",
]

TARGET_TIMING_COLUMNS: list[str] = [
    "trial_n",
    "target_frames_scheduled", "target_frames_shown",
    "target_visible_ms_scheduled", "target_visible_ms_measured",
    "late_flips_in_window", "longest_frame_interval_ms",
    "target_timing_ok",
]

SCAN_LOG_COLUMNS: list[str] = [
    "trial_n", "trial_type", "polarity", "magnitude", "phase", "tr_n",
    "phase_onset_global_time", "phase_offset_global_time",
    "phase_onset_trial_time", "phase_offset_trial_time",
    "pulse_ct",
]
