"""
Session bootstrap: the task-specific SessionInfo dataclass.

Screen + frame-timing setup, the ScreenDiagnostics dataclass, and timestamped
run-directory creation now live in the shared psyexp-core harness
(``psyexp_core.screen`` / ``psyexp_core.diagnostics`` / ``psyexp_core.rundir``).
Instruction presentation lives in mid_det.task.instructions.
"""
from __future__ import annotations

from dataclasses import dataclass

from mid_det import config


@dataclass
class SessionInfo:
    subject_id: str
    fmri: bool
    run_n: str                 # "1" | "2" | "practice"
    show_instructions: bool
    base_rt_s: float
    rt_change_s: float = config.RT_CHANGE_S   # staircase step; set by wizard
    legacy_name: str = ""                     # NAME for legacy-fmt/{NAME}_b{run}.csv
