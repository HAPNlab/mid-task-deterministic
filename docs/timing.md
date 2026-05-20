# Timing Notes

## Hit detection and frame-level display persistence

The hit/miss criterion is **"key pressed while target is visually displayed"**, not `rt_ms < target_dur_ms`. These are different because of how frame-gated display removal works.

### How removal works (`trial.py:run_response`)

Removal is gated on a clock reading against the keyboard clock, which is reset on the target-onset flip:

```python
should_remove = (
    target_removed_at is None
    and target_onset_flip_done
    and kb.clock.getTime() >= target_dur_s - frame_dur_s
)
```

The threshold is reduced by `frame_dur_s` (`1.0 / frame_rate`) because `win.flip()` blocks until the next VSYNC after the check — the post-flip timestamp lands ~one frame above whatever the threshold was. Subtracting up front makes `target_dur_ms_actual` land near `target_dur_ms` rather than one frame above it.

`frame_dur_s` is computed at session start from `win.getActualFrameRate()`. If PsychoPy can't get a stable measurement (it returns `None`, or a value outside 30–200 Hz), `frame_dur_s` stays `None` and the compensation is skipped — `target_dur_ms_actual` will overshoot by ~one frame, but at least it's not corrupted by a guessed frame period. The console prints a warning so you notice. This typically indicates VSYNC isn't working (common on macOS dev rigs); on a properly VSYNC'd scanner display the measurement succeeds and compensation kicks in.

### Why a clock-based check (and not frame counting)

A frame-counting implementation — drawing the target for exactly `round(target_dur_s / frame_dur_s)` flips — is conceptually cleaner and produces deterministically frame-quantized durations, but it requires that `win.flip()` actually blocks on VSYNC. On macOS we observed runs where `flip()` returned without waiting for the vertical blank (PsychoPy logs "Multiple dropped frames have occurred"), in which case the loop counts "frames" that never made it to the screen. Clock-based gating tolerates this because `kb.clock` advances in real time regardless of what the compositor is doing.

`session.py:setup_screen` still passes `waitBlanking=True` and calls `winHandle.set_vsync(True)` so that the scanner display (where VSYNC is reliable) gets proper frame-accurate timing — but the trial loop does not depend on it.

### History

Earlier iterations of this logic had three problems, each addressed in turn:

1. **Wrong reference point** (`(phase_clock.getTime() − jitter_s) >= target_dur_s`): `kb.clock` is reset at the actual onset flip, not when `phase_clock` crossed `jitter_s`. The offset between those two moments could push the recorded `target_dur_ms_actual` up to ~16 ms *short* of `target_dur_ms`.
2. **One-frame overshoot**: switching the check to `kb.clock.getTime() >= target_dur_s` removed the undershoot but produced a consistent ~16 ms overshoot from the post-flip frame.
3. **Frame counting at unknown rate**: subtracting `frame_dur_s` cancelled most of the overshoot, but boundary jitter occasionally bumped trials one frame earlier (11–17 ms outliers). A switch to frame counting fixed the outliers on machines with working VSYNC, but failed catastrophically on macOS dev rigs where VSYNC was silently broken — producing 133 ms durations for a 265 ms target.

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
