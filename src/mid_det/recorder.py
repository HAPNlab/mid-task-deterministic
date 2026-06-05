"""
Data recording: TrialRecord, ScanPhase, CsvWriter, ScanLogWriter, write_manifest.
"""
from __future__ import annotations

import csv
import json
import math
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


def _psychopy_version() -> str:
    try:
        import psychopy  # type: ignore
        return getattr(psychopy, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def _system_info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": _cpu_name(),
        "os_name": platform.system(),
        "os_release": platform.release(),
        "python_version": platform.python_version(),
        "psychopy_version": _psychopy_version(),
        "git_commit": _git_commit(),
    }


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

LEGACY_MID_COLUMNS: list[str] = [
    "trial", "TR", "trialonset", "trialtype", "target_ms", "rt", "cue_value",
    "hit", "trial_gain", "total", "iti", "drift",
    "total_winpercent", "binned_winpercent",
]

SCAN_LOG_COLUMNS: list[str] = [
    "trial_n", "trial_type", "polarity", "magnitude", "phase", "tr_n",
    "phase_onset_global_time", "phase_offset_global_time",
    "phase_onset_trial_time", "phase_offset_trial_time",
    "pulse_ct",
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


def _num2str(x: float) -> str:
    """Format a number like MATLAB's default ``num2str`` (used throughout
    PartialParseData.m). Default precision is ``%g`` with
    ``max(floor(log10(|x|)), 0) + 5`` significant figures, so values < 1 (drift,
    win-percents) get 5 sig figs (``0.16667``, ``-0.00011858``) and larger
    magnitudes get more (``12.013``). ``%g`` collapses whole values (``1.0`` →
    ``"1"``) and only uses scientific notation for exponents < -4."""
    if x == 0:
        return "0"
    sig = max(math.floor(math.log10(abs(x))), 0) + 5
    return f"{x:.{sig}g}"


def _legacy_cue_value(polarity: str, magnitude: int) -> str:
    """Legacy cue-value string (MATLAB PresentCue.m): gain → "+$X", loss → "-$X".
    The sign is always shown, including for magnitude 0 (e.g. "+$0" / "-$0")."""
    sign = "+" if polarity == "gain" else "-"
    return f"{sign}${magnitude}"


def _legacy_trial_gain(polarity: str, magnitude: int, hit: int) -> str:
    """Legacy realised-gain string (MATLAB PresentFeedback.m `valuestr`):
      gain + hit  → "+$mag"   gain + miss → "$0"
      loss + hit  → "$0"      loss + miss → "-$mag"
    """
    if polarity == "gain":
        return f"+${magnitude}" if hit else "$0"
    return "$0" if hit else f"-${magnitude}"


def _legacy_total(total: int) -> str:
    """Legacy running total (MATLAB PartialParseData.m: ['$' num2str(total,'%#4.2f')]).
    Negatives render as "$-1.00", non-negatives as "$0.00" / "$12.00"."""
    return f"${total:.2f}"


class LegacyMidCsvWriter:
    """Writes the legacy MATLAB MID CSV (one row per TR) for downstream-system
    compatibility. Tracks cumulative win-rate counters across appended trials.

    *trial_offset* is added to each trial number to mirror MATLAB
    PartialParseData.m, which numbers block-2 trials starting at 43 (offset 42).
    """

    def __init__(self, path: Path, trial_offset: int = 0) -> None:
        self._file = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=LEGACY_MID_COLUMNS)
        self._writer.writeheader()
        self._trial_offset = trial_offset
        self._n_hits = 0
        self._n_trials = 0
        self._type_hits: dict[int, int] = {}
        self._type_trials: dict[int, int] = {}

    def append(self, record: TrialRecord) -> None:
        self._n_trials += 1
        self._n_hits += record.hit
        self._type_trials[record.trial_type] = self._type_trials.get(record.trial_type, 0) + 1
        self._type_hits[record.trial_type] = self._type_hits.get(record.trial_type, 0) + record.hit

        total_winpercent = self._n_hits / self._n_trials
        binned_winpercent = (
            self._type_hits[record.trial_type] / self._type_trials[record.trial_type]
        )
        # MATLAB rt_vector: -2 = early press, -1 = miss/too-slow, else RT (seconds).
        if record.early_press:
            rt: float = -2
        elif isinstance(record.rt_ms, str):  # "" sentinel = miss/too-slow
            rt = -1
        else:
            rt = record.rt_ms / 1000
        # Float columns are formatted with _num2str to match MATLAB's default
        # num2str precision; integer and dollar-string columns are left as-is.
        row = {
            "trial": record.trial_n + self._trial_offset,
            "TR": 0,  # filled per row below
            "trialonset": _num2str(record.time_onset),
            "trialtype": record.trial_type,
            "target_ms": _num2str(record.target_dur_ms / 1000),
            "rt": _num2str(rt),
            "cue_value": _legacy_cue_value(record.polarity, record.magnitude),
            "hit": record.hit,
            "trial_gain": _legacy_trial_gain(record.polarity, record.magnitude, record.hit),
            "total": _legacy_total(record.total_earned),
            "iti": record.n_iti_trs * 2,
            "drift": _num2str(record.timing_drift_ms / 1000),
            "total_winpercent": _num2str(total_winpercent),
            "binned_winpercent": _num2str(binned_winpercent),
        }
        for tr in range(1, record.total_trs + 1):
            row["TR"] = tr
            self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()


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
        "system": _system_info(),
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


def write_ratings_manifest(
    run_dir: Path,
    subject_id: str,
    show_instructions: bool,
    session_time: datetime,
    screen_diag: "ScreenDiagnostics",
    win_res: list[int],
    n_cues: int,
    scale_points: int,
) -> None:
    """Write manifest.json for a cue-ratings survey run.

    The survey is self-paced (no scanner sync / frame-timing), so this is a
    trimmed version of write_manifest — no study_params or frame-rate fields.
    """
    from mid_det import __version__

    manifest = {
        "mid_task_deterministic_version": __version__,
        "task": "cue-ratings",
        "subject_id": subject_id,
        "show_instructions": show_instructions,
        "session_time": session_time.isoformat(timespec="seconds"),
        "n_cues": n_cues,
        "scale_points": scale_points,
        "system": _system_info(),
        "display": {
            "gl_vendor": screen_diag.gl_vendor,
            "gl_renderer": screen_diag.gl_renderer,
            "win_type": screen_diag.win_type,
            "pyglet_version": screen_diag.pyglet_version,
            "resolution": [int(x) for x in win_res],
        },
        "process": {"argv": sys.argv},
    }
    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
