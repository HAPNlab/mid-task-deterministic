"""
FlipTimer: accumulates per-flip timing for the response window and derives the
target-display diagnostics consumed by run_trial. Fed ``win.lastFrameT`` once per
flip. Kept separate from the timing-critical response loop in response.py so the
measurement bookkeeping can be read (and tested) in isolation.
"""
from __future__ import annotations


class FlipTimer:
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
