"""
The response window: target onset/offset timing and keypress capture.

run_response is the timing-critical core of a trial. It uses
psychopy.hardware.keyboard.Keyboard for accurate RT timestamping. _FlipTimer
accumulates per-flip diagnostics; _ResponseState classifies the keypress
outcome. No rendering objects are built here; no data is written here.
"""
from __future__ import annotations

from dataclasses import dataclass

from mid_det import config
from mid_det._psychopy import core, keyboard, visual
from mid_det.debug import DebugOverlay
from mid_det.display import Stimuli, draw_fixation_x, draw_target
from mid_det.phases import _check_quit


class _FlipTimer:
    """Accumulates per-flip timing for the response window and derives the
    target-display diagnostics. Fed ``win.lastFrameT`` once per flip.

    Measurement uses ``win.lastFrameT`` — the time PsychoPy stamps inside
    ``flip()`` right after the GPU finishes the swap (after glFinish, before
    callOnFlip callbacks fire). It is a tighter proxy for the actual swap time
    than reading ``core.getTime()`` after ``flip()`` returns, which additionally
    absorbs callback-dispatch overhead.
    """

    def __init__(self, win, frame_dur_s: float, n_target_frames: int) -> None:
        self._win = win
        self._frame_dur_s = frame_dur_s
        self._n_target_frames = n_target_frames
        self._response_start_flip_t: float | None = None
        self._onset_flip_t: float | None = None
        self._removal_flip_t: float | None = None
        self._flip_iters = 0
        self._dropped_at_onset: int | None = None
        self._max_intra_flip_ms = 0.0
        self._last_intra_flip_t: float | None = None

    def on_flip(self, last_frame_t: float) -> None:
        """Call after every flip. Stamps the first flip of the response window so
        the pre-target jitter wall time can be reported later."""
        if self._response_start_flip_t is None:
            self._response_start_flip_t = last_frame_t

    def on_onset(self, last_frame_t: float) -> None:
        """Call on the flip that puts the target on the glass."""
        self._onset_flip_t = last_frame_t
        self._dropped_at_onset = getattr(self._win, "nDroppedFrames", 0)
        self._last_intra_flip_t = last_frame_t

    def on_target_frame(self, last_frame_t: float) -> None:
        """Call after each flip while the target is on screen. A stretched flip
        interval here is the DWM-hiccup signature; keep the worst one."""
        self._flip_iters += 1
        self._accumulate_interval(last_frame_t)
        self._last_intra_flip_t = last_frame_t

    def on_removal(self, last_frame_t: float) -> float | None:
        """Call on the flip that clears the target. Returns ``target_removed_at``
        (onset→removal wall seconds), or None if onset was never stamped."""
        self._removal_flip_t = last_frame_t
        # Measure the interval into the removal flip too — a stretched removal
        # flip is exactly the DWM-hiccup signature and must not be invisible.
        self._accumulate_interval(last_frame_t)
        if self._onset_flip_t is None:
            return None
        return last_frame_t - self._onset_flip_t

    def _accumulate_interval(self, last_frame_t: float) -> None:
        if self._last_intra_flip_t is not None:
            delta_ms = (last_frame_t - self._last_intra_flip_t) * 1000
            if delta_ms > self._max_intra_flip_ms:
                self._max_intra_flip_ms = delta_ms

    def summary(self) -> dict:
        """Build the diagnostics dict consumed by run_trial."""
        if self._onset_flip_t is not None and self._removal_flip_t is not None:
            onset_to_removal_wall_ms = round(
                (self._removal_flip_t - self._onset_flip_t) * 1000, 2
            )
        else:
            onset_to_removal_wall_ms = ""

        if self._response_start_flip_t is not None and self._onset_flip_t is not None:
            jitter_ms_actual = round(
                (self._onset_flip_t - self._response_start_flip_t) * 1000, 2
            )
        else:
            jitter_ms_actual = ""

        if self._dropped_at_onset is not None:
            dropped_frames = int(
                getattr(self._win, "nDroppedFrames", 0) - self._dropped_at_onset
            )
        else:
            dropped_frames = 0

        # Mark trial unclean if (a) PsychoPy detected any dropped frames during the
        # response window, OR (b) the measured wall delta differs from the expected
        # on-screen duration by more than half a frame. Either condition makes the
        # exact target-display time unreliable for timing-sensitive analyses; flag
        # for exclusion at analysis time. DWM-induced extra frames on Windows are
        # an acknowledged unsolvable limitation — exclusion is the standard fix.
        expected_dur_ms = self._n_target_frames * self._frame_dur_s * 1000
        half_frame_ms = (self._frame_dur_s * 1000) / 2
        timing_off_by_frame = (
            isinstance(onset_to_removal_wall_ms, (int, float))
            and abs(onset_to_removal_wall_ms - expected_dur_ms) > half_frame_ms
        )
        trial_clean = dropped_frames == 0 and not timing_off_by_frame

        return {
            "flip_iters": self._flip_iters,
            "n_target_frames": self._n_target_frames,
            "dropped_frames": dropped_frames,
            "onset_to_removal_wall_ms": onset_to_removal_wall_ms,
            "max_flip_interval_ms": round(self._max_intra_flip_ms, 2),
            "trial_clean": trial_clean,
            "jitter_ms_actual": jitter_ms_actual,
        }


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

    timer = _FlipTimer(win, frame_dur_s, n_target_frames)
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

        _check_quit(kb, overlay)

    return (
        response.hit,
        response.rt_s,
        response.early_press,
        target_removed_at,
        timer.summary(),
    )
