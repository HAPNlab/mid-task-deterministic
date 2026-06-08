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

from psychopy import prefs

prefs.hardware["keyboardBackend"] = "ptb"

from psychopy import visual
from psychopy.hardware import keyboard
from rich.console import Console

from mid_det import recorder, session
from mid_det.ratings import core as rcore
from mid_det.ratings import display as rdisplay
from mid_det.ratings.setup_wizard import run_ratings_wizard

_PACKAGE_DIR = Path(__file__).resolve().parent          # src/mid_det/ratings/
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent.parent        # project root
_TEXT_DIR = _PROJECT_ROOT / "text"

# Slider control keys (MATLAB parity): 1 = left, 2 = right, 3 = select/advance.
_KEY_LEFT = "1"
_KEY_RIGHT = "2"
_KEY_SELECT = "3"
_ADVANCE_KEYS = [_KEY_LEFT, _KEY_RIGHT, _KEY_SELECT]
# Instruction/text pages advance on button 1 only (forward-only, no going back).
_PAGE_ADVANCE_KEYS = [_KEY_LEFT]
_QUIT_KEYS = ["escape"]


def _load_instruction_pages() -> list[str]:
    path = _TEXT_DIR / "instructions_ratings.txt"
    pages: list[str] = []
    with open(path) as f:
        for line in f:
            stripped = line.rstrip()
            if stripped:
                pages.append(stripped)
    return pages


def _wait_keys(kb: keyboard.Keyboard, key_list: list[str]):
    """Block until one of *key_list* (or escape) is pressed; return the name.
    Escape quits the survey."""
    kb.clearEvents()
    while True:
        pressed = kb.getKeys(keyList=key_list + _QUIT_KEYS, waitRelease=False)
        if pressed:
            name = pressed[0].name
            if name in _QUIT_KEYS:
                core.quit()
            return name


def _show_text_page(
    win: visual.Window,
    kb: keyboard.Keyboard,
    text_stim: visual.TextStim,
    hint_stim: visual.TextStim,
    text: str,
) -> None:
    text_stim.text = text
    text_stim.draw()
    hint_stim.draw()
    win.flip()
    _wait_keys(kb, _PAGE_ADVANCE_KEYS)


def _run_slider(
    win: visual.Window,
    kb: keyboard.Keyboard,
    stim: rdisplay.RatingStimuli,
    scale: str,
    cue: rcore.RatingCue | None,
) -> int:
    """Run one slider interaction; return the selected position (1..N_ELS)."""
    pos = rcore.START_SLIDEPOS[scale]
    rdisplay.draw_scale(stim, scale, pos, cue)
    win.flip()
    while True:
        key = _wait_keys(kb, _ADVANCE_KEYS)
        if key == _KEY_LEFT:
            pos = rcore.clamp_slider(pos, -1)
        elif key == _KEY_RIGHT:
            pos = rcore.clamp_slider(pos, +1)
        elif key == _KEY_SELECT:
            return pos
        rdisplay.draw_scale(stim, scale, pos, cue)
        win.flip()


def _show_fixation(win: visual.Window, stim: rdisplay.RatingStimuli) -> None:
    rdisplay.draw_fixation(stim)
    win.flip()
    core.wait(0.5)


def run() -> None:
    # ── SCREEN ───────────────────────────────────────────────────────────────
    win_res, win, screen_diag = session.setup_screen()

    # ── WIZARD ───────────────────────────────────────────────────────────────
    subject_id, show_instructions, legacy_name = run_ratings_wizard()
    session_time = datetime.now()

    rcon = Console(stderr=True)
    rcon.print(f"[bold]Cue-ratings survey:[/bold] subject=[cyan]{subject_id}[/cyan]")

    # ── RUN DIR + MANIFEST ───────────────────────────────────────────────────
    # Write the manifest up front (mirroring the MID task) so session metadata is
    # captured even if the survey is aborted before the CSV is written at the end.
    ts = session_time.strftime("%Y%m%dT%H%M%S")
    run_dir = _PROJECT_ROOT / "data" / f"{subject_id}_ratings_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    recorder.write_ratings_manifest(
        run_dir=run_dir,
        subject_id=subject_id,
        show_instructions=show_instructions,
        session_time=session_time,
        screen_diag=screen_diag,
        win_res=win_res,
        n_cues=len(rcore.RATING_CUES),
        scale_points=rcore.N_ELS,
    )

    # ── KEYBOARD ─────────────────────────────────────────────────────────────
    kb = keyboard.Keyboard()
    actual_backend = kb.device.getBackend()
    if actual_backend != "ptb":
        win.close()
        raise RuntimeError(
            f"Keyboard backend is '{actual_backend}', not 'ptb'. "
            "Install psychtoolbox: pip install psychtoolbox"
        )
    kb.device.muteOutsidePsychopy = False
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

    pages = _load_instruction_pages()
    # pages: 0=intro, 1=valence, 2=arousal, 3=independence, 4=final

    # ── INSTRUCTIONS + PRACTICE DEMOS ────────────────────────────────────────
    if show_instructions:
        _show_text_page(win, kb, instr_text, instr_hint, pages[0])
        _show_text_page(win, kb, instr_text, instr_hint, pages[1])
        _run_slider(win, kb, stim, "valence", cue=None)   # valence practice demo
        _show_text_page(win, kb, instr_text, instr_hint, pages[2])
        _run_slider(win, kb, stim, "arousal", cue=None)   # arousal practice demo
        _show_text_page(win, kb, instr_text, instr_hint, pages[3])

    # Final "press 3 to select" page is always shown (MATLAB inst5).
    _show_text_page(win, kb, instr_text, instr_hint, pages[4])

    # ── RATING TRIALS ────────────────────────────────────────────────────────
    _show_fixation(win, stim)
    results: list[dict] = []
    for cue in rcore.RATING_CUES:
        valence = _run_slider(win, kb, stim, "valence", cue)
        arousal = _run_slider(win, kb, stim, "arousal", cue)
        results.append({
            "polarity": cue.polarity, "magnitude": cue.magnitude,
            "valence": valence, "arousal": arousal,
        })
        _show_fixation(win, stim)

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
    core.wait(1.5)

    win.close()
    core.quit()


if __name__ == "__main__":
    run()
