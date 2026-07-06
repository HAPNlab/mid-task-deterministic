"""
Interactive screens for the cue-ratings survey: text pages, the slider
interaction loop, and the inter-trial fixation. Each shows one screen and waits
for input, owning the draw + key-poll loops (I/O + response logic) so that
mid_det.ratings.display stays a pure draw layer and mid_det.ratings.__main__ a
thin orchestrator.

Ported from MATLAB RunRatings.m.
"""
from __future__ import annotations

from pathlib import Path

from psychopy import core, visual
from psychopy.hardware import keyboard
from psyexp_core.keyboard import wait_for_key

from mid_det import config
from mid_det.ratings import core as rcore
from mid_det.ratings import display as rdisplay

# Slider control keys (MATLAB parity): 1 = left, 2 = right, 3 = select/advance.
KEY_LEFT = "1"
KEY_RIGHT = "2"
KEY_SELECT = "3"
ADVANCE_KEYS = [KEY_LEFT, KEY_RIGHT, KEY_SELECT]
# Instruction/text pages advance on button 1 only (forward-only, no going back).
PAGE_ADVANCE_KEYS = [KEY_LEFT]


def load_instruction_pages(text_dir: Path) -> list[str]:
    path = text_dir / "instructions_ratings.txt"
    pages: list[str] = []
    with open(path) as f:
        for line in f:
            stripped = line.rstrip()
            if stripped:
                pages.append(stripped)
    return pages


def show_text_page(
    win: visual.Window,
    kb: keyboard.Keyboard | None,
    text_stim: visual.TextStim,
    hint_stim: visual.TextStim,
    text: str,
) -> None:
    text_stim.text = text
    text_stim.draw()
    hint_stim.draw()
    win.flip()
    wait_for_key(kb, PAGE_ADVANCE_KEYS, quit_keys=config.QUIT_KEYS)


def run_slider(
    win: visual.Window,
    kb: keyboard.Keyboard | None,
    stim: rdisplay.RatingStimuli,
    scale: str,
    cue: rcore.RatingCue | None,
) -> int:
    """Run one slider interaction; return the selected position (1..N_ELS)."""
    pos = rcore.START_SLIDEPOS[scale]
    rdisplay.draw_scale(stim, scale, pos, cue)
    win.flip()
    while True:
        key = wait_for_key(kb, ADVANCE_KEYS, quit_keys=config.QUIT_KEYS)
        if key == KEY_LEFT:
            pos = rcore.clamp_slider(pos, -1)
        elif key == KEY_RIGHT:
            pos = rcore.clamp_slider(pos, +1)
        elif key == KEY_SELECT:
            return pos
        rdisplay.draw_scale(stim, scale, pos, cue)
        win.flip()


def show_fixation(win: visual.Window, stim: rdisplay.RatingStimuli) -> None:
    rdisplay.draw_fixation(stim)
    win.flip()
    core.wait(0.5)
