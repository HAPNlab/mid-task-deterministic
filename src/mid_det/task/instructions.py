"""
Instruction presentation: pages through text/instructions_MID.txt (one page per
non-blank line) via the shared psyexp_core instruction pager, then waits for the
start key. The task owns the pages and how each is drawn; the harness owns the
flip + key-polling navigation loop.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from psychopy import visual
from psychopy.hardware import keyboard
from psyexp_core import instructions as core_instructions
from psyexp_core.keyboard import get_keys
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

    def _draw_page(page: str, _is_last: bool) -> None:
        stimuli.instr_prompt.text = page
        stimuli.instr_prompt.draw()
        stimuli.instr_first.draw()

    core_instructions.page_through(
        win,
        pages,
        _draw_page,
        forward_keys=[forward_key],
        quit_keys=[end_key],
        kb=kb,
    )

    rcon.print(
        f"[bold yellow]End of instructions — press '{start_key}' to continue...[/bold yellow]"
    )
    while True:
        stimuli.instr_finish.draw()
        win.flip()
        if get_keys(kb, [start_key]):
            break
