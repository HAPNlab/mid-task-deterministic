"""
The modern per-trial CSV writers: a generic CsvWriter plus the behavioral,
target-timing, and scan-log writers that bind it to a fixed column schema. The
MATLAB legacy-format writer lives in legacy.py.
"""
from __future__ import annotations

import csv
from pathlib import Path

from mid_det.io.recording.records import (
    BEHAVIORAL_COLUMNS,
    SCAN_LOG_COLUMNS,
    TARGET_TIMING_COLUMNS,
    ScanPhase,
    TargetTimingRecord,
    TrialRecord,
)


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
