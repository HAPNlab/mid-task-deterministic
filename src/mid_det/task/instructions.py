"""
Instruction presentation: a self-paced, keypress-driven loop that pages through
text/instructions_MID.txt (one page per non-blank line) and waits for the start
key. Same draw → flip → poll pattern as the per-phase loops in phases.py, but
shown once before the trial loop rather than per trial.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from psychopy import core, visual
from psychopy.hardware import keyboard
from rich.console import Console

from mid_det import config

if TYPE_CHECKING:
    from mid_det.io.bootstrap import SessionInfo

_PROJECT_ROOT = Path(__file__).resolve().parents[3]   # src/mid_det/task/ -> project root
_TEXT_DIR = _PROJECT_ROOT / "text"


def _load_pages(path: Path) -> list[str]:
    """Read an instruction text file into a list of pages (one non-blank line each)."""
    pages: list[str] = []
    with open(path) as f:
        for line in f:
            stripped = line.rstrip()
            if stripped:
                pages.append(stripped)
    return pages


def display_instructions(
    win: visual.Window,
    stimuli,              # Stimuli dataclass from display.py; avoid circular import
    session_info: "SessionInfo",
    kb: keyboard.Keyboard,
    rcon: Console,
) -> None:
    """Display instructions from text/instructions_MID.txt one page at a time."""
    keys_map = config.KEYS_FMRI if session_info.fmri else config.KEYS_BEHAVIORAL
    forward_key = keys_map["forward"]
    start_key = keys_map["start"]
    end_key = keys_map["end"]

    pages = _load_pages(_TEXT_DIR / "instructions_MID.txt")
    if not pages:
        return

    kb.clearEvents()
    page_idx = 0

    while True:
        stimuli.instr_prompt.text = pages[page_idx]
        stimuli.instr_prompt.draw()
        stimuli.instr_first.draw()
        win.flip()

        pressed = kb.getKeys(keyList=[forward_key, end_key], waitRelease=False)
        if not pressed:
            continue
        key_name = pressed[0].name
        if key_name == end_key:
            core.quit()
        elif key_name == forward_key:
            page_idx += 1
            if page_idx >= len(pages):
                break

    rcon.print(
        f"[bold yellow]End of instructions — press '{start_key}' to continue...[/bold yellow]"
    )
    while True:
        stimuli.instr_finish.draw()
        win.flip()
        if kb.getKeys(keyList=[start_key], waitRelease=False):
            break
