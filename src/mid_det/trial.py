"""
Phase functions and run_trial().
Uses psychopy.hardware.keyboard.Keyboard for accurate RT timestamping.
No rendering objects are built here; no data is written here.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable

import pandas as pd
from psychopy import core, logging, visual
from psychopy.hardware import keyboard

from mid_det import config
from mid_det.calibration import CalibrationState
from mid_det.debug import DebugOverlay
from mid_det.display import (
    Stimuli,
    draw_cue,
    draw_feedback,
    draw_fixation_o,
    draw_fixation_x,
    draw_target,
)
from mid_det.recorder import ScanPhase, TargetTimingRecord, TrialRecord
from mid_det.scanner import PulseCounter


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
    target_shown = False
    target_onset_flip_done = False
    target_removed_at: float | None = None
    clock_reset_scheduled = False
    hit = False
    rt_s: float | None = None

    # Measurement: use win.lastFrameT (the time PsychoPy stamps inside flip(),
    # right after glFinish but before callOnFlip callbacks fire). This is a
    # tighter proxy for the actual swap time than reading core.getTime() after
    # flip() returns, which additionally absorbs callback-dispatch overhead.
    response_start_flip_t: float | None = None
    onset_flip_t: float | None = None
    removal_flip_t: float | None = None
    flip_iters = 0
    dropped_at_onset: int | None = None
    max_intra_flip_ms = 0.0
    last_intra_flip_t: float | None = None

    # Drain any presses queued between fixation end and now (e.g. during
    # pulse_counter.wait_for_tr() or scheduler hiccups). Any EXP_KEYS press
    # observed here belongs to the pre-target window and must count as early.
    # Plain kb.clearEvents() would silently discard these.
    if kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False):
        early_press = True

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

    while phase_clock.getTime() < config.STUDY_TIMES_S["response"]:
        t = phase_clock.getTime()

        # Schedule kb.clock reset to fire on the next flip so t=0 aligns with target onset
        if not clock_reset_scheduled and t >= jitter_s:
            win.callOnFlip(kb.clock.reset)
            clock_reset_scheduled = True
            target_shown = True

        if target_onset_flip_done and target_removed_at is None:
            frames_shown = round(kb.clock.getTime() / frame_dur_s) + 1
        else:
            frames_shown = 0
        should_remove = (
            target_removed_at is None
            and target_onset_flip_done
            and frames_shown >= n_target_frames
        )

        # Draw before flip: omitting draw_target when should_remove clears the target on this flip
        if target_shown and target_removed_at is None and not should_remove:
            draw_target(stimuli)
        elif not target_shown:
            draw_fixation_x(stimuli)
        win.flip()

        # Stamp the first flip of the response phase so we can later report the
        # actual pre-target jitter wall time (analog of target_dur_ms_actual).
        if response_start_flip_t is None:
            response_start_flip_t = win.lastFrameT

        # Timestamp using win.lastFrameT, which PsychoPy sets inside flip()
        # right after the GPU finishes the swap. core.getTime() after flip()
        # returns would additionally include callOnFlip callback overhead.
        if should_remove:
            removal_flip_t = win.lastFrameT
            target_removed_at = removal_flip_t - onset_flip_t if onset_flip_t else None
            # Also measure the interval into the removal flip — a stretched
            # removal flip is exactly the DWM-hiccup signature and must not be
            # invisible to the diagnostic.
            if last_intra_flip_t is not None:
                delta_ms = (removal_flip_t - last_intra_flip_t) * 1000
                if delta_ms > max_intra_flip_ms:
                    max_intra_flip_ms = delta_ms
        elif clock_reset_scheduled and not target_onset_flip_done:
            target_onset_flip_done = True
            onset_flip_t = win.lastFrameT
            dropped_at_onset = getattr(win, "nDroppedFrames", 0)
            last_intra_flip_t = onset_flip_t

        if target_onset_flip_done and target_removed_at is None:
            flip_iters += 1
            now = win.lastFrameT
            if last_intra_flip_t is not None:
                delta_ms = (now - last_intra_flip_t) * 1000
                if delta_ms > max_intra_flip_ms:
                    max_intra_flip_ms = delta_ms
            last_intra_flip_t = now

        # Poll keys after flip so timestamps are relative to the most recent screen state
        if not target_shown and not early_press:
            if kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False):
                early_press = True

        if target_shown and not hit and rt_s is None and not early_press:
            keys = kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False)
            if keys:
                rt = keys[0].rt
                if rt < 0:
                    early_press = True
                else:
                    rt_s = rt
                    if target_removed_at is None or rt < target_removed_at:
                        hit = True

        _check_quit(kb, overlay)

    if onset_flip_t is not None and removal_flip_t is not None:
        onset_to_removal_wall_ms = round(
            (removal_flip_t - onset_flip_t) * 1000, 2
        )
    else:
        onset_to_removal_wall_ms = ""

    if response_start_flip_t is not None and onset_flip_t is not None:
        jitter_ms_actual = round((onset_flip_t - response_start_flip_t) * 1000, 2)
    else:
        jitter_ms_actual = ""

    if dropped_at_onset is not None:
        dropped_frames = int(getattr(win, "nDroppedFrames", 0) - dropped_at_onset)
    else:
        dropped_frames = 0

    # Mark trial unclean if (a) PsychoPy detected any dropped frames during the
    # response window, OR (b) the measured wall delta differs from the expected
    # on-screen duration by more than half a frame. Either condition makes the
    # exact target-display time unreliable for timing-sensitive analyses; flag
    # for exclusion at analysis time. DWM-induced extra frames on Windows are
    # an acknowledged unsolvable limitation — exclusion is the standard fix.
    expected_dur_ms = n_target_frames * frame_dur_s * 1000
    half_frame_ms = (frame_dur_s * 1000) / 2
    timing_off_by_frame = (
        isinstance(onset_to_removal_wall_ms, (int, float))
        and abs(onset_to_removal_wall_ms - expected_dur_ms) > half_frame_ms
    )
    trial_clean = dropped_frames == 0 and not timing_off_by_frame

    diagnostics = {
        "flip_iters": flip_iters,
        "n_target_frames": n_target_frames,
        "dropped_frames": dropped_frames,
        "onset_to_removal_wall_ms": onset_to_removal_wall_ms,
        "max_flip_interval_ms": round(max_intra_flip_ms, 2),
        "trial_clean": trial_clean,
        "jitter_ms_actual": jitter_ms_actual,
    }

    return hit, rt_s, early_press, target_removed_at, diagnostics


def _compute_reward(
    hit: bool, polarity: str, magnitude: int, total_earned: int
) -> tuple[str, int]:
    """
    Return (reward_outcome_label, new_total_earned).

    Gain trial:  hit → +$magnitude, miss → $0
    Loss trial:  hit → $0,          miss → -$magnitude
    """
    if polarity == "gain":
        if hit and magnitude > 0:
            return f"+${magnitude}.00", total_earned + magnitude
        if hit and magnitude == 0:
            return "+$0.00", total_earned
        return "$0.00", total_earned

    # loss
    if hit:
        return "$0.00", total_earned
    if magnitude > 0:
        return f"-${magnitude}.00", total_earned - magnitude
    return "-$0.00", total_earned


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


def run_trial(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    global_clock: core.Clock,
    row: pd.Series,
    trial_n: int,
    n_trials: int,
    n_iti_trs: int,
    nominal_time: float,
    total_earned: int,
    subject_id: str,
    run_n: str,
    pulse_ct: int,
    pulse_counter: PulseCounter,
    calibration: CalibrationState,
    frame_dur_s: float,
    on_window: Callable[[int], None] | None = None,
    on_response: Callable[[bool, float | None, bool, int, float | str, str, int], None] | None = None,
    overlay: DebugOverlay | None = None,
) -> tuple[TrialRecord, TargetTimingRecord, list[ScanPhase], float, int]:
    """
    Run one complete trial (cue → fixation → response → outcome → ITI).

    Returns (record, target_timing, scan_phases, nominal_time, total_earned).
    """
    polarity = str(row["polarity"])
    magnitude = int(row["magnitude"])
    trial_type = config.TRIAL_TYPE_MAP[(polarity, magnitude)]
    target_dur_s = calibration.next_target_dur_s(polarity, magnitude)
    jitter_s = random.uniform(
        config.JITTER_MIN_S,
        config.JITTER_MAX_S,
    )
    label = config.cue_label(polarity, magnitude)

    target_dur_ms = int(round(target_dur_s * 1000))
    logging.exp(
        f"Trial {trial_n:3d}/{n_trials}  cue={label}  "
        f"target_dur={target_dur_ms} ms  jitter={int(jitter_s * 1000)} ms"
    )
    if on_window is not None:
        on_window(target_dur_ms)

    scan_phases: list[ScanPhase] = []
    tr_within = 0

    def _update_overlay(phase: str) -> None:
        if overlay is not None:
            overlay.state.phase = phase
            overlay.state.polarity = polarity
            overlay.state.magnitude = magnitude
            overlay.state.target_dur_ms = target_dur_ms
            overlay.state.jitter_ms = int(jitter_s * 1000)
            overlay.state.pulse_ct = pulse_ct
            overlay.state.global_time = global_clock.getTime()
            overlay.state.nominal_time = nominal_time

    # ── CUE ─────────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.drain()
    time_onset = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="cue", tr_n=tr_within,
        phase_onset_global_time=time_onset,
        phase_onset_trial_time=0.0,
        pulse_ct=pulse_ct,
    ))
    _update_overlay("cue")
    run_cue(win, stimuli, polarity, magnitude, kb, overlay)
    nominal_time += config.STUDY_TIMES_S["cue"]

    # ── FIXATION ──────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    fixation_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="fixation", tr_n=tr_within,
        phase_onset_global_time=fixation_start,
        phase_onset_trial_time=fixation_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    _update_overlay("fixation")
    early_press = run_fixation(win, stimuli, kb, overlay)
    nominal_time += config.STUDY_TIMES_S["fixation"]

    # ── RESPONSE ─────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    response_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="response", tr_n=tr_within,
        phase_onset_global_time=response_start,
        phase_onset_trial_time=response_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    _update_overlay("response")
    hit, rt_s, early_press, target_removed_at, response_diag = run_response(
        win, stimuli, kb, jitter_s, target_dur_s, frame_dur_s, early_press, overlay
    )
    nominal_time += config.STUDY_TIMES_S["response"]
    target_dur_ms_actual = round(target_removed_at * 1000, 2) if target_removed_at is not None else ""
    reward_outcome, total_earned = _compute_reward(hit, polarity, magnitude, total_earned)
    if on_response is not None:
        on_response(
            hit, rt_s, early_press, target_dur_ms, target_dur_ms_actual,
            reward_outcome, total_earned,
        )

    # ── OUTCOME ──────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    outcome_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="outcome", tr_n=tr_within,
        phase_onset_global_time=outcome_start,
        phase_onset_trial_time=outcome_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    _update_overlay("outcome")
    show_outcome(win, stimuli, kb, hit, reward_outcome, overlay)
    nominal_time += config.STUDY_TIMES_S["outcome"]
    calibration.record_outcome(polarity, magnitude, bool(hit))

    # ── ITI ──────────────────────────────────────────────────────────────────
    for _ in range(n_iti_trs):
        pulse_ct += pulse_counter.wait_for_tr()
        iti_start = global_clock.getTime()
        tr_within += 1
        scan_phases.append(ScanPhase(
            trial_n=trial_n, phase="post-outcome-fixation", tr_n=tr_within,
            phase_onset_global_time=iti_start,
            phase_onset_trial_time=iti_start - time_onset,
            pulse_ct=pulse_ct,
        ))
        actual_time = global_clock.getTime()
        iti_dur = config.STUDY_TIMES_S["iti"] - (actual_time - nominal_time)
        nominal_time += config.STUDY_TIMES_S["iti"]
        _update_overlay("iti")
        run_iti(win, stimuli, kb, iti_dur, overlay)

    # ── BUILD RECORD ─────────────────────────────────────────────────────────
    time_trial_end = global_clock.getTime()
    time_sched_end = nominal_time

    record = TrialRecord(
        trial_n=trial_n,
        trial_type=trial_type,
        polarity=polarity,
        magnitude=magnitude,
        cue_label=label,
        time_onset=round(time_onset, 6),
        jitter_ms=int(round(jitter_s * 1000)),
        jitter_ms_actual=response_diag["jitter_ms_actual"],
        target_dur_ms=target_dur_ms,
        target_dur_ms_actual=target_dur_ms_actual,
        early_press=int(early_press),
        hit=int(hit),
        rt_ms=round(rt_s * 1000, 2) if rt_s is not None else "",
        reward_outcome=reward_outcome,
        total_earned=total_earned,
        time_trial_end=round(time_trial_end, 6),
        trial_dur_ms=int(round((time_trial_end - time_onset) * 1000)),
        time_sched_end=round(time_sched_end, 6),
        timing_drift_ms=round((time_trial_end - time_sched_end) * 1000, 2),
        n_iti_trs=n_iti_trs,
        total_trs=tr_within,
        subject_id=subject_id,
        run_n=run_n,
        pulse_ct=scan_phases[0].pulse_ct,
    )

    target_timing = TargetTimingRecord(
        trial_n=trial_n,
        target_frames_scheduled=response_diag["n_target_frames"],
        target_frames_shown=response_diag["flip_iters"],
        target_visible_ms_scheduled=round(
            response_diag["n_target_frames"] * frame_dur_s * 1000, 2
        ),
        target_visible_ms_measured=response_diag["onset_to_removal_wall_ms"],
        late_flips_in_window=response_diag["dropped_frames"],
        longest_frame_interval_ms=response_diag["max_flip_interval_ms"],
        target_timing_ok=int(response_diag["trial_clean"]),
    )

    if overlay is not None:
        overlay.state.last_result = "HIT" if record.hit else ("early" if record.early_press else "miss")
        overlay.state.last_rt_ms = f"{record.rt_ms:.0f} ms" if record.rt_ms != "" else "—"
        overlay.state.last_timing_drift_ms = record.timing_drift_ms

    return record, target_timing, scan_phases, nominal_time, total_earned
