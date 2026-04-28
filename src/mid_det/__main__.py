"""
Entry point: `python -m mid_det` or `mid-task-det` script.
Wires all modules together.
"""
from __future__ import annotations


def run() -> None:
    # Disable pyglet event checking in background threads (prevents macOS crash)
    from psychopy import core
    core.checkPygletDuringWait = False

    from datetime import datetime
    from pathlib import Path

    from psychopy import event as psy_event, logging
    from psychopy.hardware import keyboard
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    import rich.box

    from mid_det import config, display, recorder, scanner, session, trial
    from mid_det.calibration import CalibrationState

    # ── INITIALISE SESSION ───────────────────────────────────────────────────
    session_info = session.show_dialog()
    session_time = datetime.now()

    win_res, win = session.setup_screen()

    measured_fps = win.getActualFrameRate()
    frame_rate = measured_fps if (measured_fps is not None and measured_fps < 200) else 60.0

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
    rcon.print(f"[bold]Frame rate:[/bold] {frame_rate:.1f} Hz")
    logging.exp(f"Session: subject={session_info.subject_id}  run={session_info.run_n}  fmri={session_info.fmri}")
    logging.exp(f"Frame rate: {frame_rate:.1f} Hz")

    # ── BUILD STIMULI ────────────────────────────────────────────────────────
    stimuli_obj = display.build_stimuli(win)
    display.update_instr_keys(stimuli_obj, session_info.fmri)

    # ── LOAD SEQUENCE ────────────────────────────────────────────────────────
    sequence = session.load_sequence(session_info.run_n)
    n_trials = len(sequence)

    # ── ADAPTIVE CALIBRATION ────────────────────────────────────────────────
    base_rt_s = session_info.base_rt_s
    calibration = CalibrationState(base_rt_s=base_rt_s)
    rcon.print(
        f"[bold]Adaptive target window:[/bold] base=[cyan]{int(base_rt_s * 1000)} ms[/cyan]  "
        f"step=±[cyan]{int(config.RT_CHANGE_S * 1000)} ms[/cyan]  "
        f"win-ratio threshold=[cyan]{config.WIN_RATIO_THRESHOLD}[/cyan]"
    )
    logging.exp(
        f"Adaptive target window: base={int(base_rt_s * 1000)} ms  "
        f"step=±{int(config.RT_CHANGE_S * 1000)} ms  "
        f"win-ratio threshold={config.WIN_RATIO_THRESHOLD}"
    )

    # ── SETUP OUTPUT FILES ───────────────────────────────────────────────────
    file_stem = f"{session_info.subject_id}_run{session_info.run_n}"
    behavioral_writer = recorder.BehavioralCsvWriter(run_dir / f"behavioral_{file_stem}.csv")
    scan_log_writer = recorder.ScanLogWriter(run_dir / f"scan_log_{file_stem}.csv")
    recorder.write_manifest(
        run_dir=run_dir,
        session_info=session_info,
        session_time=session_time,
        frame_rate=frame_rate,
        n_trials=n_trials,
    )

    # ── KEYBOARD & MOUSE ─────────────────────────────────────────────────────
    kb = keyboard.Keyboard()
    win.mouseVisible = False

    # ── INSTRUCTIONS ─────────────────────────────────────────────────────────
    if session_info.show_instructions:
        session.display_instructions(win, stimuli_obj, session_info)

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
        psy_event.waitKeys(keyList=[keys_map["start"]])
    backend.start()
    rcon.print("[bold green]Scan started[/bold green] — global clock reset")
    logging.exp("Scan started — global clock reset")

    # ── GLOBAL CLOCK & INITIAL FIXATION ──────────────────────────────────────
    global_clock = core.Clock()
    global_clock.reset()

    t_fix_end = config.INITIAL_FIX_DUR_S
    while global_clock.getTime() < t_fix_end:
        stimuli_obj.fix.draw()
        win.flip()

    nominal_time = global_clock.getTime()

    # ── TRIAL LOOP ───────────────────────────────────────────────────────────
    pulse_ct = 0
    total_earned = 0
    n_hits = 0
    n_trials_done = 0

    table = Table(box=rich.box.SIMPLE_HEAD)
    table.add_column("#", justify="right")
    table.add_column("Cue")
    table.add_column("Window", justify="right")
    table.add_column("Result")
    table.add_column("RT", justify="right")
    table.add_column("Outcome", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Hit %", justify="right")

    with Live(table, console=rcon, auto_refresh=False) as live:
        for trial_idx, row in sequence.iterrows():
            trial_n = int(trial_idx) + 1
            n_iti = int(row["n_iti"])

            rec, scan_phases, nominal_time, total_earned = trial.run_trial(
                win=win,
                stimuli=stimuli_obj,
                kb=kb,
                global_clock=global_clock,
                row=row,
                trial_n=trial_n,
                n_iti_trs=n_iti,
                nominal_time=nominal_time,
                total_earned=total_earned,
                subject_id=session_info.subject_id,
                run_n=session_info.run_n,
                pulse_ct=pulse_ct,
                pulse_counter=pulse_counter,
                calibration=calibration,
            )

            if scan_phases:
                pulse_ct = scan_phases[-1].pulse_ct

            n_trials_done += 1
            n_hits += rec.hit
            hit_rate = n_hits / n_trials_done * 100
            rt_str = f"{rec.rt_ms:.0f} ms" if rec.rt_ms != "" else "—"
            result_label = "HIT" if rec.hit else ("early" if rec.early_press else "miss")
            if rec.hit:
                result_cell = "[green]HIT[/green]"
            elif rec.early_press:
                result_cell = "[yellow]early[/yellow]"
            else:
                result_cell = "[red]miss[/red]"

            table.add_row(
                f"{trial_n}/{n_trials}",
                rec.cue_label,
                f"{rec.target_dur_ms} ms",
                result_cell,
                rt_str,
                rec.reward_outcome,
                f"${rec.total_earned}",
                f"{hit_rate:.0f}%",
            )
            live.refresh()

            logging.exp(
                f"Trial {trial_n:3d}/{n_trials}  {rec.cue_label:<5}  "
                f"win={rec.target_dur_ms:3d} ms  {result_label:<5}  RT={rt_str:>6}  "
                f"outcome={rec.reward_outcome:>4}  total={f'${rec.total_earned}':>5}  "
                f"hit_rate={hit_rate:3.0f}%"
            )

            behavioral_writer.append(rec)
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
    while global_clock.getTime() < t_close_start + config.CLOSING_FIX_DUR_S:
        stimuli_obj.fix.draw()
        win.flip()

    # ── END SCREEN ───────────────────────────────────────────────────────────
    stimuli_obj.end.draw()
    win.flip()
    psy_event.waitKeys(keyList=["0"])

    # ── CLEANUP ──────────────────────────────────────────────────────────────
    behavioral_writer.close()
    scan_log_writer.close()
    logging.flush()
    win.close()
    core.quit()


if __name__ == "__main__":
    run()
