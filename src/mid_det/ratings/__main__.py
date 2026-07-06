"""
Entry point for the cue-ratings survey: `mid-ratings-det`.

A self-paced survey (no scanner sync, no frame-timing measurement). Each of the
6 MID cues is rated on a VALENCE then an AROUSAL 7-point circle-slider scale,
controlled with buttons 1 (left) / 2 (right) / 3 (select). Output is a single
CSV: data/ratings_<subject>.csv with columns polarity,magnitude,arousal,valence.

Ported from MATLAB RunRatings.m.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

# Must be set before any other PsychoPy import (prevents macOS pyglet crash).
from psychopy import core

core.checkPygletDuringWait = False

from psychopy import visual
from psyexp_core import rundir, screen
from psyexp_core.keyboard import (
    KEYBOARD_BACKEND,
    build_keyboard,
    configure_psychopy_backend,
    wait_for_key,
)
from rich.console import Console

from mid_det import config
from mid_det.io import recording
from mid_det.ratings import core as rcore
from mid_det.ratings import display as rdisplay
from mid_det.ratings import flow
from mid_det.ratings.setup_wizard import run_ratings_wizard

_PACKAGE_DIR = Path(__file__).resolve().parent          # src/mid_det/ratings/
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent.parent        # project root
_TEXT_DIR = _PROJECT_ROOT / "text"


def run() -> None:
    # Select the keyboard backend before any Keyboard is built.
    configure_psychopy_backend()

    # ── SCREEN ───────────────────────────────────────────────────────────────
    # Let the operator pick the display (auto-returns 0 when there's only one);
    # the chosen monitor is captured in screen_diag and recorded in the manifest.
    screen_index = screen.prompt_screen()
    win_res, win, screen_diag = screen.setup_screen(screen=screen_index)

    # ── WIZARD ───────────────────────────────────────────────────────────────
    subject_id, show_instructions, legacy_name = run_ratings_wizard()
    session_started_at = datetime.now()

    rcon = Console(stderr=True)
    rcon.print(f"[bold]Cue-ratings survey:[/bold] subject=[cyan]{subject_id}[/cyan]")

    # ── RUN DIR + MANIFEST ───────────────────────────────────────────────────
    # Write the manifest up front (mirroring the MID task) so session metadata is
    # captured even if the survey is aborted before the CSV is written at the end.
    run_dir = rundir.make_run_dir(
        _PROJECT_ROOT / "data", f"{subject_id}_ratings", session_started_at
    )
    recording.write_ratings_manifest(
        run_dir=run_dir,
        subject_id=subject_id,
        show_instructions=show_instructions,
        session_started_at=session_started_at,
        screen_diag=screen_diag,
        win_res=win_res,
        n_cues=len(rcore.RATING_CUES),
        scale_points=rcore.N_ELS,
    )

    # ── KEYBOARD ─────────────────────────────────────────────────────────────
    if KEYBOARD_BACKEND != "ptb":
        win.close()
        raise RuntimeError(
            f"Keyboard backend is '{KEYBOARD_BACKEND}', not 'ptb'. "
            "Install psychtoolbox: pip install psychtoolbox"
        )
    kb = build_keyboard()
    win.mouseVisible = False

    # ── STIMULI ──────────────────────────────────────────────────────────────
    stim = rdisplay.build_rating_stimuli(win)

    x_scr = float(win.size[0]) / float(win.size[1])
    instr_text = visual.TextStim(
        win, name="page_text", font="Arial", pos=(0, 0.08),
        height=1.0 / 22, color="white", wrapWidth=x_scr / 1.4, autoLog=False,
    )
    instr_hint = visual.TextStim(
        win, name="page_hint", font="Arial", text="Press button 1 to continue.",
        pos=(0, -0.38), height=1.0 / 28, color="white", autoLog=False,
    )

    pages = flow.load_instruction_pages(_TEXT_DIR)
    # pages: 0=intro, 1=valence, 2=arousal, 3=independence, 4=final

    # ── INSTRUCTIONS + PRACTICE DEMOS ────────────────────────────────────────
    if show_instructions:
        flow.show_text_page(win, kb, instr_text, instr_hint, pages[0])
        flow.show_text_page(win, kb, instr_text, instr_hint, pages[1])
        flow.run_slider(win, kb, stim, "valence", cue=None)   # valence practice demo
        flow.show_text_page(win, kb, instr_text, instr_hint, pages[2])
        flow.run_slider(win, kb, stim, "arousal", cue=None)   # arousal practice demo
        flow.show_text_page(win, kb, instr_text, instr_hint, pages[3])

    # Final "press 3 to select" page is always shown (MATLAB inst5).
    flow.show_text_page(win, kb, instr_text, instr_hint, pages[4])

    # ── RATING TRIALS ────────────────────────────────────────────────────────
    flow.show_fixation(win, stim)
    results: list[dict] = []
    for cue in rcore.RATING_CUES:
        valence = flow.run_slider(win, kb, stim, "valence", cue)
        arousal = flow.run_slider(win, kb, stim, "arousal", cue)
        results.append({
            "polarity": cue.polarity, "magnitude": cue.magnitude,
            "valence": valence, "arousal": arousal,
        })
        flow.show_fixation(win, stim)

    # ── WRITE CSV ────────────────────────────────────────────────────────────
    # (manifest.json was already written to run_dir at startup)
    out_path = run_dir / f"ratings_{subject_id}.csv"
    rcore.write_ratings_csv(out_path, results)

    # Legacy-format copy (gamble,arousal,valence) for downstream systems.
    legacy_dir = _PROJECT_ROOT / "data" / "legacy-fmt"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_path = legacy_dir / f"{legacy_name}_ratings.csv"
    rcore.write_legacy_ratings_csv(legacy_path, results)

    rcon.print(f"[bold green]Ratings saved[/bold green] -> [cyan]{out_path}[/cyan]")
    rcon.print(f"[bold green]Legacy ratings saved[/bold green] -> [cyan]{legacy_path}[/cyan]")
    for r in results:
        rcon.print(
            f"  {r['polarity']:<4} ${r['magnitude']}  valence=[cyan]{r['valence']}[/cyan]  "
            f"arousal=[cyan]{r['arousal']}[/cyan]"
        )

    # ── END SCREEN ───────────────────────────────────────────────────────────
    end = visual.TextStim(
        win, name="rating_end", text="Thank you!", pos=(0, 0),
        height=1.0 / 20, color="white", autoLog=False,
    )
    end.draw()
    win.flip()

    rcon.print("[bold green]Run complete[/bold green]")
    exit_key = config.END_KEYS[0]
    rcon.print(f"[bold yellow]Press '{exit_key}' to exit...[/bold yellow]")
    wait_for_key(kb, config.END_KEYS, quit_keys=config.QUIT_KEYS)

    win.close()
    core.quit()


if __name__ == "__main__":
    run()
