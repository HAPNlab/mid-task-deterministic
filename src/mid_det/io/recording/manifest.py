"""
Run manifest writers (manifest.json): write_manifest for a task run,
write_ratings_manifest for a cue-ratings survey run. Both delegate to the shared
``psyexp_core.manifest.write_manifest``, which fills in the system / display /
process diagnostics and the resolved psyexp_core_version; this module supplies
the MID-specific top-level fields (via *header*) and parameters (*study_params*).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from psyexp_core.manifest import write_manifest as _core_write_manifest

if TYPE_CHECKING:
    from psyexp_core.diagnostics import ScreenDiagnostics

    from mid_det.io.bootstrap import SessionInfo


def write_manifest(
    run_dir: Path,
    session_info: "SessionInfo",
    session_started_at: datetime,
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
        CLOSING_FIX_DUR_S,
        INITIAL_FIX_DUR_S,
        JITTER_MAX_S,
        JITTER_MIN_S,
        MIN_TRIALS_FOR_ADAPT,
        MR_SETTINGS,
        WIN_RATIO_THRESHOLD,
    )

    header = {
        "mid_task_deterministic_version": __version__,
        "subject_id": session_info.subject_id,
        "run_n": session_info.run_n,
        "fmri": session_info.fmri,
        "show_instructions": session_info.show_instructions,
    }
    study_params = {
        "tr_duration_s": MR_SETTINGS["TR"],
        "initial_fix_dur_s": INITIAL_FIX_DUR_S,
        "closing_fix_dur_s": CLOSING_FIX_DUR_S,
        "base_rt_s": session_info.base_rt_s,
        "rt_change_s": session_info.rt_change_s,
        "win_ratio_threshold": WIN_RATIO_THRESHOLD,
        "min_trials_for_adapt": MIN_TRIALS_FOR_ADAPT,
        "jitter_min_s": JITTER_MIN_S,
        "jitter_max_s": JITTER_MAX_S,
    }
    _core_write_manifest(
        run_dir,
        header=header,
        session_time=session_started_at,
        screen_diag=screen_diag,
        win_res=win_res,
        study_params=study_params,
        frame_rate=frame_rate,
        n_trials=n_trials,
        frame_dur_s=frame_dur_s,
        frame_dur_source=frame_dur_source,
        extra_process={"priority_raised": priority_raised},
    )


def write_ratings_manifest(
    run_dir: Path,
    subject_id: str,
    show_instructions: bool,
    session_started_at: datetime,
    screen_diag: "ScreenDiagnostics",
    win_res: list[int],
    n_cues: int,
    scale_points: int,
) -> None:
    """Write manifest.json for a cue-ratings survey run.

    The survey is self-paced (no scanner sync / frame-timing), so this passes no
    study_params or frame-rate fields — just the survey header and display block.
    """
    from mid_det import __version__

    header = {
        "mid_task_deterministic_version": __version__,
        "task": "cue-ratings",
        "subject_id": subject_id,
        "show_instructions": show_instructions,
        "n_cues": n_cues,
        "scale_points": scale_points,
    }
    _core_write_manifest(
        run_dir,
        header=header,
        session_time=session_started_at,
        screen_diag=screen_diag,
        win_res=win_res,
    )
