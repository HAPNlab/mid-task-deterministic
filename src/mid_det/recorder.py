"""
Data recording: TrialRecord, ScanPhase, CsvWriter, ScanLogWriter, write_manifest.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mid_det.session import SessionInfo


@dataclass
class TrialRecord:
    trial_n: int
    trial_type: int
    valence: str
    magnitude: int
    cue_label: str
    time_onset: float
    jitter_ms: int
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
    total_trs: int
    subject_id: str
    run_n: str
    pulse_ct: int
    flip_iters: int
    n_target_frames: int
    dropped_frames: int
    onset_to_removal_wall_ms: float | str


@dataclass
class ScanPhase:
    trial_n: int
    phase: str
    tr_n: int
    phase_global_time: float
    phase_trial_time: float
    pulse_ct: int


BEHAVIORAL_COLUMNS: list[str] = [
    "trial_n", "trial_type", "valence", "magnitude", "cue_label",
    "time_onset", "jitter_ms", "target_dur_ms", "target_dur_ms_actual", "early_press", "hit", "rt_ms",
    "reward_outcome", "total_earned", "time_trial_end", "trial_dur_ms",
    "time_sched_end", "timing_drift_ms", "total_trs", "subject_id", "run_n",
    "pulse_ct",
    "flip_iters", "n_target_frames", "dropped_frames", "onset_to_removal_wall_ms",
]

SCAN_LOG_COLUMNS: list[str] = [
    "trial_n", "phase", "tr_n", "phase_global_time", "phase_trial_time", "pulse_ct",
]


class CsvWriter:
    def __init__(self, path: Path, columns: list[str]) -> None:
        self._file = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=columns)
        self._writer.writeheader()
        self._columns = columns

    def append(self, record: object) -> None:
        row = {k: getattr(record, k) for k in self._columns}
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class BehavioralCsvWriter(CsvWriter):
    def __init__(self, path: Path) -> None:
        super().__init__(path, BEHAVIORAL_COLUMNS)

    def append(self, record: TrialRecord) -> None:  # type: ignore[override]
        super().append(record)


class ScanLogWriter(CsvWriter):
    def __init__(self, path: Path) -> None:
        super().__init__(path, SCAN_LOG_COLUMNS)

    def append(self, phase: ScanPhase) -> None:  # type: ignore[override]
        super().append(phase)


def write_manifest(
    run_dir: Path,
    session_info: "SessionInfo",
    session_time: datetime,
    frame_rate: float,
    n_trials: int,
) -> None:
    from mid_det import __version__
    from mid_det.config import (
        MR_SETTINGS,
        INITIAL_FIX_DUR_S,
        CLOSING_FIX_DUR_S,
        WIN_RATIO_THRESHOLD,
        MIN_TRIALS_FOR_ADAPT,
        JITTER_MIN_S,
        JITTER_MAX_S,
    )

    manifest = {
        "mid_task_deterministic_version": __version__,
        "subject_id": session_info.subject_id,
        "run_n": session_info.run_n,
        "fmri": session_info.fmri,
        "show_instructions": session_info.show_instructions,
        "session_time": session_time.isoformat(timespec="seconds"),
        "frame_rate_hz": round(frame_rate, 3),
        "n_trials": n_trials,
        "study_params": {
            "tr_duration_s": MR_SETTINGS["TR"],
            "initial_fix_dur_s": INITIAL_FIX_DUR_S,
            "closing_fix_dur_s": CLOSING_FIX_DUR_S,
            "base_rt_s": session_info.base_rt_s,
            "rt_change_s": session_info.rt_change_s,
            "win_ratio_threshold": WIN_RATIO_THRESHOLD,
            "min_trials_for_adapt": MIN_TRIALS_FOR_ADAPT,
            "jitter_min_s": JITTER_MIN_S,
            "jitter_max_s": JITTER_MAX_S,
        },
    }
    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
