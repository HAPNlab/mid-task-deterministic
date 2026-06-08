"""Data recording: trial-record dataclasses, the per-trial CSV writers (modern
and legacy MATLAB formats), and the run-manifest writers. The public API is
re-exported here so callers can use ``mid_det.io.recording`` directly."""
from __future__ import annotations

from mid_det.io.recording.csv_writers import (
    BehavioralCsvWriter,
    CsvWriter,
    ScanLogWriter,
    TargetTimingCsvWriter,
)
from mid_det.io.recording.legacy import LEGACY_MID_COLUMNS, LegacyMidCsvWriter
from mid_det.io.recording.manifest import write_manifest, write_ratings_manifest
from mid_det.io.recording.records import (
    BEHAVIORAL_COLUMNS,
    SCAN_LOG_COLUMNS,
    TARGET_TIMING_COLUMNS,
    ScanPhase,
    TargetTimingRecord,
    TrialRecord,
)

__all__ = [
    "BEHAVIORAL_COLUMNS",
    "TARGET_TIMING_COLUMNS",
    "SCAN_LOG_COLUMNS",
    "LEGACY_MID_COLUMNS",
    "TrialRecord",
    "TargetTimingRecord",
    "ScanPhase",
    "CsvWriter",
    "BehavioralCsvWriter",
    "TargetTimingCsvWriter",
    "ScanLogWriter",
    "LegacyMidCsvWriter",
    "write_manifest",
    "write_ratings_manifest",
]
