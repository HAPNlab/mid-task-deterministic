"""
The legacy MATLAB MID CSV path (one row per TR) for downstream-system
compatibility, plus the num2str/dollar-string formatting helpers that reproduce
the MATLAB PartialParseData.m / PresentCue.m / PresentFeedback.m output exactly.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from mid_det.io.recording.records import TrialRecord

LEGACY_MID_COLUMNS: list[str] = [
    "trial", "TR", "trialonset", "trialtype", "target_ms", "rt", "cue_value",
    "hit", "trial_gain", "total", "iti", "drift",
    "total_winpercent", "binned_winpercent",
]


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
