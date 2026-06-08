"""
Trial orchestration: run_trial() ties the per-phase loops together (cue →
fixation → response → outcome → ITI), applies the reward rule, and builds the
data records. The per-phase display loops live in phases.py and the
timing-critical response window in response.py. No rendering objects are built
here; no data is written here.
"""
from __future__ import annotations

import random
from collections.abc import Callable

import pandas as pd

from mid_det import config
from mid_det._psychopy import core, keyboard, logging, visual
from mid_det.task.calibration import CalibrationState
from mid_det.task.debug import DebugOverlay
from mid_det.task.display import Stimuli
from mid_det.task.phases import run_cue, run_fixation, run_iti, show_outcome
from mid_det.io.recording import ScanPhase, TargetTimingRecord, TrialRecord
from mid_det.task.response import run_response
from mid_det.io.scanner import PulseCounter


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
    # Drift is measured here — at the end of feedback, before the ITI — to match
    # MATLAB main.m:329 (`GetSecs()-abs_start-onset_t(i)-8.0`). It is the per-trial
    # over/under-run of the four fixed slides relative to this trial's own onset,
    # i.e. the slippage the ITI is about to correct, NOT the post-correction
    # residual. In scan mode the per-phase wait_for_tr() waits fall inside this
    # window, so any TR-lock slack is included (same as the prior definition).
    time_outcome_end = global_clock.getTime()

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

    # Backfill each phase's end = onset of the next phase (tiled timeline);
    # the final phase ends at the trial end.
    for i, sp in enumerate(scan_phases):
        end_global = (
            scan_phases[i + 1].phase_onset_global_time
            if i + 1 < len(scan_phases)
            else time_trial_end
        )
        sp.phase_offset_global_time = end_global
        sp.phase_offset_trial_time = end_global - time_onset
        sp.trial_type = trial_type
        sp.polarity = polarity
        sp.magnitude = magnitude

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
        timing_drift_ms=round(
            ((time_outcome_end - time_onset) - config.PRE_ITI_NOMINAL_S) * 1000, 2
        ),
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
