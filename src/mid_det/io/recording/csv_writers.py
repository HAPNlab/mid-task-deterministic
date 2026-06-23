"""
The modern per-trial CSV writers: the behavioral, target-timing, and scan-log
writers that bind the shared ``psyexp_core.recording.CsvWriter`` to a fixed
column schema. The MATLAB legacy-format writer lives in legacy.py.
"""
from __future__ import annotations

from pathlib import Path

from psyexp_core.recording import CsvWriter

from mid_det.io.recording.records import (
    BEHAVIORAL_COLUMNS,
    SCAN_LOG_COLUMNS,
    TARGET_TIMING_COLUMNS,
    ScanPhase,
    TargetTimingRecord,
    TrialRecord,
)


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
