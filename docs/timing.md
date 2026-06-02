# Timing Notes

## Hit detection and frame-level display persistence

The hit/miss criterion is **"key pressed while target is visually displayed"**, not `rt_ms < target_dur_ms`. These are different because of how frame-gated display removal works.

### How removal works (`trial.py:run_response`)

Removal is **frame-counted**. At session start we measure the refresh rate, compute `n_target_frames = round(target_dur_s / frame_dur_s)`, then draw the target for exactly that many flips and omit it on the next:

```python
frames_shown = round(kb.clock.getTime() / frame_dur_s) + 1
should_remove = (
    target_removed_at is None
    and target_onset_flip_done
    and frames_shown >= n_target_frames
)
```

`frames_shown` is derived from `kb.clock` (reset on the target-onset flip via `callOnFlip`) rather than counted from loop iterations. The clock advances with wall time, so a dropped frame — one `flip()` that spans two vsync intervals — bumps `frames_shown` by 2 and removal happens one iteration sooner. Loop-iteration counting would tick once and leave the target on for one extra frame. Windows occasionally drops a frame even with VSYNC enabled; the clock-derived count absorbs it. `target_dur_ms_actual` (read from `kb.clock` on the removal flip) lands within a few hundred µs of `n_target_frames * frame_dur_s`.

### Refresh rate must be known at startup

`frame_dur_s` comes from `win.getActualFrameRate()`. If PsychoPy can't get a stable measurement (returns `None`, or a value outside 30–200 Hz), `__main__.run()` raises `RuntimeError` rather than guessing — a wrong frame period silently corrupts every target duration. The user can override with `--fps <hz>` if they know the refresh rate but VSYNC measurement is broken (e.g. macOS dev rigs, where the Cocoa compositor doesn't honor `set_vsync(True)`).

`session.py:setup_screen` passes `waitBlanking=True` and calls `winHandle.set_vsync(True)` so production Windows rigs flip on VSYNC.

### macOS caveat

On macOS, `win.flip()` often returns before the next vertical blank — PsychoPy logs "Multiple dropped frames have occurred" — and frame counting will produce wildly wrong durations (e.g. 133 ms for a 265 ms target). This is a known macOS/Cocoa compositor issue we can't fix in software. Production runs on Windows; macOS is dev-only and, if used, requires passing `--fps` manually with the understanding that recorded durations will not match wall time.

### History

Earlier iterations of this logic went through several problems:

1. **Wrong reference point** (`(phase_clock.getTime() − jitter_s) >= target_dur_s`): `kb.clock` is reset at the actual onset flip, not when `phase_clock` crossed `jitter_s`. The offset between those two moments could push the recorded `target_dur_ms_actual` up to ~16 ms *short* of `target_dur_ms`.
2. **One-frame overshoot**: switching the check to `kb.clock.getTime() >= target_dur_s` removed the undershoot but produced a consistent ~16 ms overshoot from the post-flip frame.
3. **Boundary jitter outliers**: subtracting `frame_dur_s` from a clock threshold cancelled most of the overshoot, but boundary jitter occasionally bumped trials one frame earlier (11–17 ms outliers).
4. **Brief detour through a clock-based gate** to tolerate broken macOS VSYNC. Reverted in favor of frame counting once we accepted that production is Windows-only and macOS dev sessions must pass `--fps` explicitly.
5. **Iteration-counted frames**: an initial frame-counting implementation incremented a `target_frames_drawn` counter once per loop iteration. On Windows this overshot by exactly one frame on the ~20% of trials where a frame dropped — each dropped frame leaves the target visible for an extra vsync but only ticks the counter once. Fixed by deriving the count from `kb.clock` instead.

### Why this can't be solved in software (frame overshoot)

The frame boundary is the fundamental constraint. Stimulus removal is display-synchronous — the target can only disappear at a VSYNC. At 60 Hz that quantizes all removal times to multiples of 16.67 ms, so there will always be up to one frame of overshoot between `target_dur_ms` and actual display duration. A higher refresh rate monitor reduces this: 120 Hz → ~8 ms max overshoot, 240 Hz → ~4 ms. The hit detection logic correctly reflects this reality by tying the hit/miss decision to the visual state (`target_removed`) rather than a numeric RT threshold.

### Example: trial 29, XXX000 run 1

| field             | value  |
|-------------------|--------|
| `target_dur_ms`   | 325    |
| `rt_ms`           | 330.98 |
| `hit`             | 1      |
| `timing_drift_ms` | 2.73   |

The frame started before the 325 ms threshold (`t - jitter_s < 325 ms` → `target_removed = False`), the key was pressed 330.98 ms after onset within that same frame, and `getKeys()` caught it after the flip while `target_removed` was still False. The monitor was showing the target at the moment of the keypress. The hit is correct.

### What `rt_ms > target_dur_ms` means in the data

It is expected and valid. With one-frame compensation, `target_dur_ms_actual` can be slightly above or below `target_dur_ms` (depending on how `target_dur_s` rounds to the nearest frame), but `target_dur_ms_actual` is always the true cutoff. Any hit with `rt_ms < target_dur_ms_actual` is a response to a stimulus that was visually present.

---

## CSV timing precision vs. video recording

The behavioral CSV is the **ground truth** for timing. All timestamps come from high-resolution system clocks:

- `rt_ms` — hardware keyboard timestamp from `kb.clock` (sub-millisecond)
- `time_onset` — `core.Clock` system timer (sub-millisecond)

OBS screen capture at 60 fps gives **16.67 ms resolution** plus ~1 frame of capture latency from the macOS compositor. The +/- variation seen when comparing CSV timings to OBS frame positions is expected and is an artifact of OBS, not the task.

OBS recording is useful for:
- Visually confirming stimuli rendered correctly
- Spotting obvious dropped frames or display glitches

OBS recording is **not** suitable for:
- Measuring absolute stimulus onset times
- Validating sub-frame RT precision

For dropped frame detection, PsychoPy supports `win.recordFrameIntervals = True`, which logs per-flip timing and can flag VSYNCs that were missed. This would reveal cases where a stimulus was inadvertently displayed for an extra frame beyond the expected rounding.

---

## OBS recording settings for visual auditing

If recording with OBS for frame-by-frame inspection:

- **Encoder**: Apple ProRes 422 LT (intra-frame; every frame independently decodable)
- **Format**: Hybrid MOV
- **FPS**: 60 (match display refresh rate)
- **Resolution**: 1920×1080 (match Dell P2419HC)
- **Show cursor**: off
- **Source**: Display Capture → Dell P2419HC

Avoid H.264 for timing audits — inter-frame compression makes frame-accurate inspection harder, though modern editors (Premiere, Resolve) can still step frame-by-frame.
