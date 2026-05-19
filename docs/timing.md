# Timing Notes

## Hit detection and frame-level display persistence

The hit/miss criterion is **"key pressed while target is visually displayed"**, not `rt_ms < target_dur_ms`. These are different because of how frame-gated display removal works.

### How removal works (`trial.py:run_response`)

At the top of each loop iteration, `t = phase_clock.getTime()` is captured. The target is removed (not drawn) on the iteration where `(t - jitter_s) >= target_dur_s`. Because `t` is the **frame start** time, the target stays on screen through the flip of that last frame and remains visible until the *next* flip.

At 60 Hz (16.67 ms/frame), a `target_dur_ms = 325` target is displayed for:

```
ceil(325 / 16.67) × 16.67 ≈ 333 ms  (20 frames)
```

So `rt_ms` values up to ~333 ms can legitimately be hits for a 325 ms target — the participant responded while the target was still physically on screen.

### Why this can't be solved in software

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

It is expected and valid. It reflects the frame-level granularity of display timing: the target can persist for up to one full frame (16.67 ms at 60 Hz) beyond `target_dur_ms`. Any hit with `rt_ms` up to approximately `target_dur_ms + frame_duration` is a response to a stimulus that was visually present.

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
