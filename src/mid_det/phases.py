"""
Fixed-duration per-phase display loops: cue, fixation, outcome, ITI, plus the
shared quit/overlay poll. Each function drives win.flip() for its STUDY_TIMES_S
duration; no data is recorded here. The timing-critical response window lives in
response.py.
"""
from __future__ import annotations

from mid_det import config
from mid_det._psychopy import core, keyboard, visual
from mid_det.debug import DebugOverlay
from mid_det.display import (
    Stimuli,
    draw_cue,
    draw_feedback,
    draw_fixation_o,
    draw_fixation_x,
)


def run_cue(
    win: visual.Window,
    stimuli: Stimuli,
    polarity: str,
    magnitude: int,
    kb: keyboard.Keyboard,
    overlay: DebugOverlay | None = None,
) -> None:
    """Display cue for STUDY_TIMES_S['cue'] seconds."""
    timer = core.CountdownTimer(config.STUDY_TIMES_S["cue"])
    while timer.getTime() > 0:
        draw_cue(stimuli, polarity, magnitude)
        win.flip()
        _check_quit(kb, overlay)


def run_fixation(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    overlay: DebugOverlay | None = None,
) -> bool:
    """Display fixation; return True if any response key was pressed (early press)."""
    kb.clearEvents()
    early = False
    timer = core.CountdownTimer(config.STUDY_TIMES_S["fixation"])
    while timer.getTime() > 0:
        draw_fixation_x(stimuli)
        win.flip()
        _check_quit(kb, overlay)
        # Poll in the loop so a press doesn't sit in the buffer until end-of-phase,
        # where a downstream kb.clearEvents() could discard it before inspection.
        if not early and kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False):
            early = True
    if not early and kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False):
        early = True
    return early


def show_outcome(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    hit: bool,
    reward_outcome: str,
    overlay: DebugOverlay | None = None,
) -> None:
    """Display the outcome feedback for STUDY_TIMES_S['outcome'] seconds."""
    timer = core.CountdownTimer(config.STUDY_TIMES_S["outcome"])
    while timer.getTime() > 0:
        draw_feedback(stimuli, hit, reward_outcome)
        win.flip()
        _check_quit(kb, overlay)


def run_iti(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    fix_dur_s: float,
    overlay: DebugOverlay | None = None,
) -> None:
    """Display fixation for fix_dur_s seconds (drift-corrected by caller)."""
    if fix_dur_s <= 0:
        return
    timer = core.CountdownTimer(fix_dur_s)
    while timer.getTime() > 0:
        draw_fixation_o(stimuli)
        win.flip()
        _check_quit(kb, overlay)


def _check_quit(kb: keyboard.Keyboard, overlay: DebugOverlay | None = None) -> None:
    if kb.getKeys(keyList=["escape"], waitRelease=False):
        core.quit()
    if overlay is not None and kb.getKeys(keyList=["f3"], waitRelease=False):
        overlay.toggle()
