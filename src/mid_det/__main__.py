"""
Entry point: `python -m mid_det` or `mid-task-det` script.
Wires all modules together.
"""
from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path

# Must be set before any other PsychoPy import (prevents macOS pyglet crash).
from psychopy import core

core.checkPygletDuringWait = False

from psychopy import logging, prefs

prefs.hardware["keyboardBackend"] = "ptb"

from psychopy.hardware import keyboard
from rich.console import Console

from mid_det import config, display, recorder, scanner, sequences, session, setup_wizard, trial
from mid_det.calibration import CalibrationState
from mid_det.console import TrialLiveView
from mid_det.debug import DebugOverlay, DebugState


def _raise_process_priority() -> str | None:
    """Bump this process to high priority on Windows to reduce scheduler-induced
    vsync stretches. Returns a short status string for the log, or None if not
    applicable / unavailable."""
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        HIGH_PRIORITY_CLASS = 0x00000080
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.kernel32.SetPriorityClass(handle, HIGH_PRIORITY_CLASS):
            return "HIGH_PRIORITY_CLASS"
        return f"SetPriorityClass failed (GetLastError={ctypes.windll.kernel32.GetLastError()})"
    except Exception as e:
        return f"unavailable ({e!r})"


def run() -> None:
    priority_status = _raise_process_priority()

    import argparse
    parser = argparse.ArgumentParser(prog="mid-task-det")
    parser.add_argument(
        "--fps", type=float, default=None, metavar="HZ",
        help="Override refresh rate used for timing compensation (e.g. 60). "
             "Bypasses getActualFrameRate(); useful when VSYNC measurement fails.",
    )
    args = parser.parse_args()

    # ── SCREEN & FRAME RATE ──────────────────────────────────────────────────
    # Open the window first so we have a real frame duration to pass into the
    # setup wizard (it uses it for RT-field defaults and frame-alignment hints).
    win_res, win, screen_diag = session.setup_screen()

    # Warm-up flips before frame-rate measurement: PsychoPy's detectingFrameDrops
    # doc notes drops are common during startup as the GPU/driver settle.
    for _ in range(30):
        win.flip()

    if args.fps is not None:
        frame_rate: float = args.fps
        frame_dur_s: float = 1.0 / args.fps
        fps_source = "specified"
    elif 1000.0 / 200.0 <= screen_diag.calib_median_ms <= 1000.0 / 30.0:
        # Prefer the 120-flip VSYNC-calibration median: it's a more reliable
        # estimator than getActualFrameRate(), and the response loop's
        # `round(t / frame_dur_s)` termination is sensitive to small drift in
        # frame_dur_s (see Windows run where 0.5% off triggered off-by-one
        # iters on long-target trials).
        frame_dur_s = screen_diag.calib_median_ms / 1000.0
        frame_rate = 1.0 / frame_dur_s
        fps_source = "vsync-calibration"
    else:
        # Fallback: getActualFrameRate(). If that also fails, bail out rather
        # than silently degrading — a guessed rate would corrupt every target
        # duration. Use --fps to override.
        measured_fps = win.getActualFrameRate()
        if measured_fps is None or not (30.0 <= measured_fps <= 200.0):
            win.close()
            raise RuntimeError(
                f"Could not measure a stable refresh rate "
                f"(getActualFrameRate() returned {measured_fps!r}). "
                "This usually means VSYNC isn't working on this display. "
                "Re-run with --fps <hz> (e.g. --fps 60) to specify it manually."
            )
        frame_rate = measured_fps
        frame_dur_s = 1.0 / measured_fps
        fps_source = "measured"

    # ── SETUP WIZARD ─────────────────────────────────────────────────────────
    session_info = setup_wizard.run_wizard(frame_dur_s=frame_dur_s)
    session_time = datetime.now()

    # ── LOGGING ──────────────────────────────────────────────────────────────
    data_dir = Path("data")
    run_dir = session.make_run_dir(data_dir, session_info, session_time)
    logging.LogFile(str(run_dir / "experiment.log"), level=logging.EXP)
    logging.console.setLevel(logging.WARNING)

    # ── RICH CONSOLE ─────────────────────────────────────────────────────────
    rcon = Console(stderr=True)
    rcon.print(
        f"[bold]Session:[/bold] subject=[cyan]{session_info.subject_id}[/cyan]  "
        f"run=[cyan]{session_info.run_n}[/cyan]  fmri=[cyan]{session_info.fmri}[/cyan]"
    )
    source_tag = "[yellow](manually specified)[/yellow]" if fps_source == "specified" else "(measured)"
    rcon.print(
        f"[bold]Frame rate:[/bold] {frame_rate:.2f} Hz  "
        f"(frame period [cyan]{frame_dur_s * 1000:.3f} ms[/cyan])  {source_tag}"
    )
    logging.exp(f"Session: subject={session_info.subject_id}  run={session_info.run_n}  fmri={session_info.fmri}")
    logging.exp(f"Frame rate: {frame_rate:.2f} Hz  (frame period {frame_dur_s * 1000:.3f} ms)  [{fps_source}]")
    logging.exp(
        f"GL vendor={screen_diag.gl_vendor}  renderer={screen_diag.gl_renderer}  "
        f"winType={screen_diag.win_type}  pyglet={screen_diag.pyglet_version}  "
        f"platform={screen_diag.platform_str}"
    )
    logging.exp(
        f"VSYNC calibration: median={screen_diag.calib_median_ms:.3f} ms  "
        f"p99={screen_diag.calib_p99_ms:.3f} ms  max={screen_diag.calib_max_ms:.3f} ms  "
        f"(n={screen_diag.calib_n})"
    )
    if priority_status is not None:
        logging.exp(f"Process priority: {priority_status}")

    # Enable per-flip interval recording for post-hoc dropped-frame analysis.
    # 1.2 * frame period is the PsychoPy-documented default threshold.
    win.refreshThreshold = frame_dur_s * 1.2
    win.recordFrameIntervals = True

    # ── BUILD STIMULI ────────────────────────────────────────────────────────
    stimuli_obj = display.build_stimuli(win)
    display.update_instr_keys(stimuli_obj, session_info.fmri)

    # ── DEBUG OVERLAY (F3 to toggle) ─────────────────────────────────────────
    debug_state = DebugState(
        subject_id=session_info.subject_id,
        run_n=session_info.run_n,
        fmri=session_info.fmri,
        frame_rate=frame_rate,
        frame_dur_ms=frame_dur_s * 1000,
    )
    debug_overlay = DebugOverlay(win, debug_state)
    _orig_flip = win.flip

    def _flip_with_overlay(*args, **kwargs):  # noqa: E306
        debug_overlay.draw()
        return _orig_flip(*args, **kwargs)

    win.flip = _flip_with_overlay

    # ── LOAD SEQUENCE ────────────────────────────────────────────────────────
    sequence = sequences.load_sequence(session_info.run_n)
    n_trials = len(sequence)
    debug_state.n_trials = n_trials

    # ── ADAPTIVE CALIBRATION ────────────────────────────────────────────────
    base_rt_s = session_info.base_rt_s
    rt_change_s = session_info.rt_change_s
    calibration = CalibrationState(base_rt_s=base_rt_s, rt_change_s=rt_change_s)
    rcon.print(
        f"[bold]Adaptive target window:[/bold] base=[cyan]{base_rt_s * 1000:.2f} ms[/cyan]  "
        f"step=±[cyan]{rt_change_s * 1000:.2f} ms[/cyan]  "
        f"win-ratio threshold=[cyan]{config.WIN_RATIO_THRESHOLD}[/cyan]"
    )
    logging.exp(
        f"Adaptive target window: base={base_rt_s * 1000:.2f} ms  "
        f"step=±{rt_change_s * 1000:.2f} ms  "
        f"win-ratio threshold={config.WIN_RATIO_THRESHOLD}"
    )

    # ── SETUP OUTPUT FILES ───────────────────────────────────────────────────
    file_stem = f"{session_info.subject_id}_run{session_info.run_n}"
    behavioral_writer = recorder.BehavioralCsvWriter(run_dir / f"behavioral_{file_stem}.csv")
    target_timing_writer = recorder.TargetTimingCsvWriter(run_dir / f"target_timing_{file_stem}.csv")
    scan_log_writer = recorder.ScanLogWriter(run_dir / f"scan_log_{file_stem}.csv")
    recorder.write_manifest(
        run_dir=run_dir,
        session_info=session_info,
        session_time=session_time,
        frame_rate=frame_rate,
        n_trials=n_trials,
        screen_diag=screen_diag,
        frame_dur_s=frame_dur_s,
        frame_dur_source=fps_source,
        win_res=win_res,
        priority_raised=(priority_status == "HIGH_PRIORITY_CLASS"),
    )

    # ── KEYBOARD & MOUSE ─────────────────────────────────────────────────────
    kb = keyboard.Keyboard()
    actual_backend = kb.device.getBackend()
    if actual_backend != "ptb":
        win.close()
        raise RuntimeError(
            f"Keyboard backend is '{actual_backend}', not 'ptb'. "
            "Install psychtoolbox: pip install psychtoolbox"
        )
    # PsychoPy ≥2024.1 defaults muteOutsidePsychopy=True on macOS, silently
    # dropping all keypresses when isRegisteredApp() returns False (common
    # when launched from a terminal or IDE). Disable it for experiment use.
    kb.device.muteOutsidePsychopy = False
    win.mouseVisible = False

    # ── INSTRUCTIONS ─────────────────────────────────────────────────────────
    if session_info.show_instructions:
        session.display_instructions(win, stimuli_obj, session_info, kb)

    # ── PULSE COUNTER ────────────────────────────────────────────────────────
    backend = scanner.make_backend(session_info.fmri)
    backend_name = "hardware (MCC DAQ)" if isinstance(backend, scanner.HardwareBackend) else "emulated"
    rcon.print(f"[bold]Scanner backend:[/bold] {backend_name}")
    logging.exp(f"Scanner backend: {backend_name}")
    pulse_counter = scanner.PulseCounter(backend)

    # ── WAIT FOR SCAN START ──────────────────────────────────────────────────
    stimuli_obj.wait.draw()
    win.flip()

    if session_info.fmri:
        rcon.print("[bold yellow]Waiting for first TR pulse...[/bold yellow]")
        logging.exp("Waiting for first TR pulse")
        pulse_counter.wait_for_start()
    else:
        keys_map = config.KEYS_BEHAVIORAL
        rcon.print(f"[bold yellow]Press '{keys_map['start']}' to start the experiment...[/bold yellow]")
        logging.exp(f"Waiting for '{keys_map['start']}' key to start experiment")
        kb.waitKeys(keyList=[keys_map["start"]], waitRelease=False)
    backend.start()
    rcon.print("[bold green]Scan started[/bold green] — global clock reset")
    logging.exp("Scan started — global clock reset")

    # ── GLOBAL CLOCK & INITIAL FIXATION ──────────────────────────────────────
    global_clock = core.Clock()
    global_clock.reset()

    is_practice = session_info.run_n == "practice"
    leadin_s = config.PRACTICE_INITIAL_FIX_DUR_S if is_practice else config.INITIAL_FIX_DUR_S
    leadout_s = config.PRACTICE_CLOSING_FIX_DUR_S if is_practice else config.CLOSING_FIX_DUR_S

    t_fix_end = leadin_s
    while global_clock.getTime() < t_fix_end:
        stimuli_obj.fix_o.draw()
        win.flip()
        if kb.getKeys(keyList=["f3"], waitRelease=False):
            debug_overlay.toggle()

    nominal_time = global_clock.getTime()

    # ── TRIAL LOOP ───────────────────────────────────────────────────────────
    pulse_ct = 0
    total_earned = 0
    n_hits = 0
    n_trials_done = 0

    with TrialLiveView(rcon, n_trials) as view:
        for trial_idx, row in sequence.iterrows():
            trial_n = int(trial_idx) + 1
            n_iti = int(row["n_iti"])
            cue_lbl = config.cue_label(str(row["polarity"]), int(row["magnitude"]))

            view.start_trial(trial_n, cue_lbl, n_hits, n_trials_done)

            debug_overlay.state.trial_n = trial_n
            debug_overlay.state.n_hits = n_hits
            debug_overlay.state.n_trials_done = n_trials_done
            debug_overlay.state.total_earned = total_earned

            rec, target_timing, scan_phases, nominal_time, total_earned = trial.run_trial(
                win=win,
                stimuli=stimuli_obj,
                kb=kb,
                global_clock=global_clock,
                row=row,
                trial_n=trial_n,
                n_trials=n_trials,
                n_iti_trs=n_iti,
                nominal_time=nominal_time,
                total_earned=total_earned,
                subject_id=session_info.subject_id,
                run_n=session_info.run_n,
                pulse_ct=pulse_ct,
                pulse_counter=pulse_counter,
                calibration=calibration,
                frame_dur_s=frame_dur_s,
                on_window=view.on_window,
                on_response=view.on_response,
                overlay=debug_overlay,
            )

            if scan_phases:
                pulse_ct = scan_phases[-1].pulse_ct

            n_trials_done += 1
            n_hits += rec.hit
            hit_rate = n_hits / n_trials_done * 100
            rt_str = f"{rec.rt_ms:.0f} ms" if rec.rt_ms != "" else "—"
            win_str = f"{rec.target_dur_ms_actual:.2f} ms" if rec.target_dur_ms_actual != "" else "—"
            result_label = "HIT" if rec.hit else ("early" if rec.early_press else "miss")

            logging.exp(
                f"  -> {result_label:<5}  RT={rt_str:>6}  win={win_str}  "
                f"outcome={rec.reward_outcome:>4}  total={f'${rec.total_earned}':>5}  "
                f"hit_rate={hit_rate:3.0f}%"
            )

            behavioral_writer.append(rec)
            target_timing_writer.append(target_timing)
            for sp in scan_phases:
                scan_log_writer.append(sp)

    rcon.print(
        f"\n[bold]Run complete:[/bold] {n_hits}/{n_trials_done} hits "
        f"([cyan]{n_hits / n_trials_done * 100:.0f}%[/cyan])  "
        f"total earned: [bold cyan]${total_earned}[/bold cyan]"
    )
    logging.exp(
        f"Run complete: {n_hits}/{n_trials_done} hits "
        f"({n_hits / n_trials_done * 100:.0f}%)  total earned: ${total_earned}"
    )

    # ── CLOSING FIXATION ─────────────────────────────────────────────────────
    t_close_start = global_clock.getTime()
    while global_clock.getTime() < t_close_start + leadout_s:
        stimuli_obj.fix_o.draw()
        win.flip()
        if kb.getKeys(keyList=["f3"], waitRelease=False):
            debug_overlay.toggle()

    # ── END SCREEN ───────────────────────────────────────────────────────────
    stimuli_obj.end.draw()
    win.flip()
    rcon.print("[bold yellow]Press '0' to exit the experiment...[/bold yellow]")
    logging.exp("Waiting for '0' key to exit experiment")
    kb.waitKeys(keyList=["0"], waitRelease=False)

    # ── CLEANUP ──────────────────────────────────────────────────────────────
    behavioral_writer.close()
    target_timing_writer.close()
    scan_log_writer.close()
    logging.flush()
    win.close()
    core.quit()


if __name__ == "__main__":
    run()
