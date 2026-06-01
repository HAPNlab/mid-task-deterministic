"""
Data recording: TrialRecord, ScanPhase, CsvWriter, ScanLogWriter, write_manifest.
"""
from __future__ import annotations

import csv
import json
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mid_det.session import ScreenDiagnostics, SessionInfo


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:  # noqa: BLE001 — diagnostic only
        return "unknown"


def _cpu_name() -> str:
    """Best-effort friendly CPU name.

    ``platform.processor()`` returns the raw CPUID descriptor on Windows
    (e.g. "Intel64 Family 6 Model 158 Stepping 11") and the bare arch on
    macOS, neither of which is a marketing name. Read the registry on
    Windows; otherwise fall back to ``platform.processor()``.
    """
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            try:
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            finally:
                winreg.CloseKey(key)
            if name:
                return str(name).strip()
        except Exception:  # noqa: BLE001 — diagnostic only
            pass
    return platform.processor() or "unknown"


@dataclass
class TrialRecord:
    trial_n: int
    trial_type: int
    valence: str
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
    dropped_frames_in_window: int
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


BEHAVIORAL_COLUMNS: list[str] = [
    "trial_n", "trial_type", "valence", "magnitude", "cue_label",
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
    "dropped_frames_in_window", "longest_frame_interval_ms",
    "target_timing_ok",
]

SCAN_LOG_COLUMNS: list[str] = [
    "trial_n", "phase", "tr_n", "phase_onset_global_time", "phase_onset_trial_time", "pulse_ct",
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


class TargetTimingCsvWriter(CsvWriter):
    def __init__(self, path: Path) -> None:
        super().__init__(path, TARGET_TIMING_COLUMNS)

    def append(self, record: TargetTimingRecord) -> None:  # type: ignore[override]
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
    screen_diag: "ScreenDiagnostics",
    frame_dur_s: float,
    frame_dur_source: str,
    win_res: list[int],
    priority_raised: bool,
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

    try:
        import psychopy  # type: ignore
        psychopy_version = getattr(psychopy, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        psychopy_version = "unknown"

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
        "system": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": _cpu_name(),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "psychopy_version": psychopy_version,
            "git_commit": _git_commit(),
        },
        "display": {
            "gl_vendor": screen_diag.gl_vendor,
            "gl_renderer": screen_diag.gl_renderer,
            "win_type": screen_diag.win_type,
            "pyglet_version": screen_diag.pyglet_version,
            "resolution": list(win_res),
            "frame_dur_ms": round(frame_dur_s * 1000, 4),
            "frame_dur_source": frame_dur_source,
            "vsync_calibration": {
                "median_ms": screen_diag.calib_median_ms,
                "p99_ms": screen_diag.calib_p99_ms,
                "max_ms": screen_diag.calib_max_ms,
                "n_samples": screen_diag.calib_n,
            },
        },
        "process": {
            "priority_raised": priority_raised,
            "argv": sys.argv,
        },
    }
    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
