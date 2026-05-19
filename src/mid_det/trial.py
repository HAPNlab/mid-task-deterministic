"""
Phase functions and run_trial().
Uses psychopy.hardware.keyboard.Keyboard for accurate RT timestamping.
No rendering objects are built here; no data is written here.
"""
from __future__ import annotations

import random
from collections.abc import Callable

import pandas as pd
from psychopy import core, logging, visual
from psychopy.hardware import keyboard

from mid_det import config
from mid_det.calibration import CalibrationState
from mid_det.display import (
    Stimuli,
    draw_cue,
    draw_feedback,
    draw_fixation_o,
    draw_fixation_x,
    draw_target,
)
from mid_det.recorder import ScanPhase, TrialRecord
from mid_det.scanner import PulseCounter


def run_cue(
    win: visual.Window,
    stimuli: Stimuli,
    valence: str,
    magnitude: int,
    kb: keyboard.Keyboard,
) -> None:
    """Display cue for STUDY_TIMES_S['cue'] seconds."""
    timer = core.CountdownTimer(config.STUDY_TIMES_S["cue"])
    while timer.getTime() > 0:
        draw_cue(stimuli, valence, magnitude)
        win.flip()
        _check_quit(kb)


def run_fixation(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
) -> bool:
    """Display fixation; return True if any response key was pressed (early press)."""
    kb.clearEvents()
    timer = core.CountdownTimer(config.STUDY_TIMES_S["fixation"])
    while timer.getTime() > 0:
        draw_fixation_x(stimuli)
        win.flip()
        _check_quit(kb)
    keys = kb.getKeys(keyList=config.EXP_KEYS, waitRelease=False)
    return len(keys) > 0


def run_response(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    jitter_s: float,
    target_dur_s: float,
    early_press: bool,
) -> tuple[bool, float | None, bool, float | None]:
    """
    Display response phase (STUDY_TIMES_S['response'] seconds total).
    Target appears after jitter_s and stays visible for target_dur_s seconds.
    Returns (hit, rt_s, early_press, target_removed_at).
    """
    phase_clock = core.Clock()
    target_shown = False
    target_removed_at: float | None = None
    clock_reset_scheduled = False
    hit = False
    rt_s: float | None = None

    # Clear stale key events before the phase begins
    kb.clearEvents()

    while phase_clock.getTime() < config.STUDY_TIMES_S["response"]:
        t = phase_clock.getTime()

        # Schedule kb.clock reset to fire on the next flip so t=0 aligns with target onset
        if not clock_reset_scheduled and t >= jitter_s:
            win.callOnFlip(kb.clock.reset)
            clock_reset_scheduled = True
            target_shown = True

        should_remove = target_removed_at is None and (t - jitter_s) >= target_dur_s

        # Draw before flip: omitting draw_target when should_remove clears the target on this flip
        if target_shown and target_removed_at is None and not should_remove:
            draw_target(stimuli)
        elif not target_shown:
            draw_fixation_x(stimuli)
        win.flip()

        # Timestamp after flip so it reflects when the target actually left the screen
        if should_remove:
            target_removed_at = kb.clock.getTime()

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

        _check_quit(kb)

    return hit, rt_s, early_press, target_removed_at


def _compute_reward(
    hit: bool, valence: str, magnitude: int, total_earned: int
) -> tuple[str, int]:
    """
    Return (reward_outcome_label, new_total_earned).

    Gain trial:  hit → +$magnitude, miss → $0
    Loss trial:  hit → $0,          miss → -$magnitude
    """
    if valence == "gain":
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


def run_outcome(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    hit: bool,
    valence: str,
    magnitude: int,
    total_earned: int,
) -> tuple[str, int]:
    """Display outcome; return (reward_outcome, new_total_earned)."""
    reward_outcome, new_total_earned = _compute_reward(hit, valence, magnitude, total_earned)
    timer = core.CountdownTimer(config.STUDY_TIMES_S["outcome"])
    while timer.getTime() > 0:
        draw_feedback(stimuli, hit, reward_outcome)
        win.flip()
        _check_quit(kb)
    return reward_outcome, new_total_earned


def run_iti(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    fix_dur_s: float,
) -> None:
    """Display fixation for fix_dur_s seconds (drift-corrected by caller)."""
    if fix_dur_s <= 0:
        return
    timer = core.CountdownTimer(fix_dur_s)
    while timer.getTime() > 0:
        draw_fixation_o(stimuli)
        win.flip()
        _check_quit(kb)


def _check_quit(kb: keyboard.Keyboard) -> None:
    if kb.getKeys(keyList=["escape", "l"], waitRelease=False):
        core.quit()


def run_trial(
    win: visual.Window,
    stimuli: Stimuli,
    kb: keyboard.Keyboard,
    global_clock: core.Clock,
    row: pd.Series,
    trial_n: int,
    n_iti_trs: int,
    nominal_time: float,
    total_earned: int,
    subject_id: str,
    run_n: str,
    pulse_ct: int,
    pulse_counter: PulseCounter,
    calibration: CalibrationState,
    on_response: Callable[[bool, float | None, bool, int, float | str], None] | None = None,
    on_outcome: Callable[[str, int, bool], None] | None = None,
) -> tuple[TrialRecord, list[ScanPhase], float, int]:
    """
    Run one complete trial (cue → fixation → response → outcome → ITI).

    Returns (record, scan_phases, nominal_time, total_earned).
    """
    valence = str(row["valence"])
    magnitude = int(row["magnitude"])
    trial_type = config.TRIAL_TYPE_MAP[(valence, magnitude)]
    target_dur_s = calibration.next_target_dur_s(valence, magnitude)
    jitter_s = random.uniform(
        config.JITTER_MIN_S,
        config.JITTER_MAX_S,
    )
    label = config.cue_label(valence, magnitude)

    target_dur_ms = int(round(target_dur_s * 1000))
    logging.exp(
        f"  -> cue={label}  target_dur={target_dur_ms} ms  "
        f"jitter={int(jitter_s * 1000)} ms"
    )

    scan_phases: list[ScanPhase] = []
    tr_within = 0

    # ── CUE ─────────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.drain()
    time_onset = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="cue", tr_n=tr_within,
        phase_global_time=time_onset,
        phase_trial_time=0.0,
        pulse_ct=pulse_ct,
    ))
    run_cue(win, stimuli, valence, magnitude, kb)
    nominal_time += config.STUDY_TIMES_S["cue"]

    # ── FIXATION ──────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    fixation_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="fixation", tr_n=tr_within,
        phase_global_time=fixation_start,
        phase_trial_time=fixation_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    early_press = run_fixation(win, stimuli, kb)
    nominal_time += config.STUDY_TIMES_S["fixation"]

    # ── RESPONSE ─────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    response_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="response", tr_n=tr_within,
        phase_global_time=response_start,
        phase_trial_time=response_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    hit, rt_s, early_press, target_removed_at = run_response(
        win, stimuli, kb, jitter_s, target_dur_s, early_press
    )
    nominal_time += config.STUDY_TIMES_S["response"]
    target_dur_ms_actual = round(target_removed_at * 1000, 2) if target_removed_at is not None else ""
    if on_response is not None:
        on_response(hit, rt_s, early_press, target_dur_ms, target_dur_ms_actual)

    # ── OUTCOME ──────────────────────────────────────────────────────────────
    pulse_ct += pulse_counter.wait_for_tr()
    outcome_start = global_clock.getTime()
    tr_within += 1
    scan_phases.append(ScanPhase(
        trial_n=trial_n, phase="outcome", tr_n=tr_within,
        phase_global_time=outcome_start,
        phase_trial_time=outcome_start - time_onset,
        pulse_ct=pulse_ct,
    ))
    reward_outcome, total_earned = run_outcome(
        win, stimuli, kb, hit, valence, magnitude, total_earned
    )
    nominal_time += config.STUDY_TIMES_S["outcome"]
    calibration.record_outcome(valence, magnitude, bool(hit))
    if on_outcome is not None:
        on_outcome(reward_outcome, total_earned, hit)

    # ── ITI ──────────────────────────────────────────────────────────────────
    for _ in range(n_iti_trs):
        pulse_ct += pulse_counter.wait_for_tr()
        iti_start = global_clock.getTime()
        tr_within += 1
        scan_phases.append(ScanPhase(
            trial_n=trial_n, phase="post-outcome-fixation", tr_n=tr_within,
            phase_global_time=iti_start,
            phase_trial_time=iti_start - time_onset,
            pulse_ct=pulse_ct,
        ))
        actual_time = global_clock.getTime()
        iti_dur = config.STUDY_TIMES_S["iti"] - (actual_time - nominal_time)
        nominal_time += config.STUDY_TIMES_S["iti"]
        run_iti(win, stimuli, kb, iti_dur)

    # ── BUILD RECORD ─────────────────────────────────────────────────────────
    time_trial_end = global_clock.getTime()
    time_sched_end = nominal_time

    record = TrialRecord(
        trial_n=trial_n,
        trial_type=trial_type,
        valence=valence,
        magnitude=magnitude,
        cue_label=label,
        time_onset=round(time_onset, 6),
        jitter_ms=int(round(jitter_s * 1000)),
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
        total_trs=tr_within,
        subject_id=subject_id,
        run_n=run_n,
        pulse_ct=scan_phases[0].pulse_ct,
    )

    return record, scan_phases, nominal_time, total_earned
