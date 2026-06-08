"""
The response window: target onset/offset timing and keypress capture.

run_response is the timing-critical core of a trial. It uses
psychopy.hardware.keyboard.Keyboard for accurate RT timestamping. FlipTimer
(flip_timer.py) accumulates per-flip diagnostics; _ResponseState classifies the
keypress outcome. No rendering objects are built here; no data is written here.
"""
from __future__ import annotations

from dataclasses import dataclass

from mid_det import config
from mid_det._psychopy import core, keyboard, visual
from mid_det.task.debug import DebugOverlay
from mid_det.task.display import Stimuli, draw_fixation_x, draw_target
from mid_det.task.flip_timer import FlipTimer
from mid_det.task.phases import _poll_hotkeys


@dataclass
class _ResponseState:
    """Captures the participant's keypress outcome for the response window."""

    early_press: bool = False
    hit: bool = False
    rt_s: float | None = None

    def poll_pretarget(self, kb: keyboard.Keyboard) -> None:
        """Before target onset any EXP_KEYS press is early. Also drains presses
        queued before the loop (e.g. during wait_for_tr); a plain
        kb.clearEvents() would silently discard those."""
        if not self.early_press and kb.getKeys(
            keyList=config.EXP_KEYS, waitRelease=False
        ):
            self.early_press = True

    def poll_target(
        self, kb: keyboard.Keyboard, target_removed_at: float | None
    ) -> None:
        """Classify the first press once the target has been shown. An rt < 0 was
        pressed before the onset-flip clock reset → early, never a hit."""
        if self.hit or self.rt_s is not None or self.early_press:
            return
        keys = kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False)
        if not keys:
            return
        rt = keys[0].rt
        if rt < 0:
            self.early_press = True
        else:
            self.rt_s = rt
            if target_removed_at is None or rt < target_removed_at:
                self.hit = True


def run_response(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    jitter_s: float,
    target_dur_s: float,
    frame_dur_s: float,
    early_press: bool,
    overlay: DebugOverlay | None = None,
) -> tuple[bool, float | None, bool, float | None, dict]:
    """
    Display response phase (STUDY_TIMES_S['response'] seconds total).
    Target appears after jitter_s and stays visible for target_dur_s seconds.
    Returns (hit, rt_s, early_press, target_removed_at, diagnostics).
    """
    phase_clock = core.Clock()
    # Two distinct moments, deliberately one flip apart (draw happens before
    # flip, pixels land on the glass when flip completes):
    target_onset_scheduled = False  # crossed jitter; onset flip is queued/decided
    target_on_screen = False  # the onset flip has happened — target is on the glass
    target_removed_at: float | None = None

    # Derive frames-shown from kb.clock (reset on the onset flip) rather than
    # counting loop iterations. Counting iterations assumes every flip() blocks
    # exactly one vsync — true on macOS once VSYNC is verified, but Windows
    # occasionally drops a frame, making one flip() span two vsyncs. The
    # iteration counter would still tick once and the target would be visible
    # for one extra frame. The clock advances with real wall time regardless,
    # so round(elapsed / frame_dur) + 1 reflects actual displayed frames.
    # round() rather than ceil() is intentional: frame-aligned durations (e.g.
    # 17 * frame_dur) accumulate floating-point drift and evaluate to
    # 17.000000000000004, which ceil() would promote to 18 — one phantom extra
    # frame. round() snaps back to the correct integer.
    n_target_frames = round(target_dur_s / frame_dur_s)

    timer = FlipTimer(win, frame_dur_s, n_target_frames)
    response = _ResponseState(early_press=early_press)

    # Drain any presses queued between fixation end and now (e.g. during
    # pulse_counter.wait_for_tr() or scheduler hiccups). Any EXP_KEYS press here
    # belongs to the pre-target window and must count as early.
    response.poll_pretarget(kb)

    while phase_clock.getTime() < config.STUDY_TIMES_S["response"]:
        t = phase_clock.getTime()

        # Schedule kb.clock reset to fire on the next flip so t=0 aligns with onset.
        if not target_onset_scheduled and t >= jitter_s:
            win.callOnFlip(kb.clock.reset)
            target_onset_scheduled = True

        # Decide removal BEFORE the flip: omitting draw_target clears the target
        # on this flip. kb.clock (reset on the onset flip) gives the wall time the
        # target has been visible; round(elapsed / frame_dur) is the whole frames
        # already shown and +1 counts the frame this upcoming flip will complete.
        should_remove = False
        if target_on_screen and target_removed_at is None:
            frames_shown_after_next_flip = round(kb.clock.getTime() / frame_dur_s) + 1
            should_remove = frames_shown_after_next_flip >= n_target_frames

        if target_onset_scheduled and target_removed_at is None and not should_remove:
            draw_target(stimuli)
        elif not target_onset_scheduled:
            draw_fixation_x(stimuli)
        win.flip()

        timer.on_flip(win.lastFrameT)
        if should_remove:
            target_removed_at = timer.on_removal(win.lastFrameT)
        elif target_onset_scheduled and not target_on_screen:
            target_on_screen = True
            timer.on_onset(win.lastFrameT)
        # The onset flip is both an onset and the target's first displayed frame.
        if target_on_screen and target_removed_at is None:
            timer.on_target_frame(win.lastFrameT)

        # Poll keys after the flip so timestamps are relative to the latest screen.
        if not target_onset_scheduled:
            response.poll_pretarget(kb)
        else:
            response.poll_target(kb, target_removed_at)

        _poll_hotkeys(kb, overlay)

    return (
        response.hit,
        response.rt_s,
        response.early_press,
        target_removed_at,
        timer.summary(),
    )
