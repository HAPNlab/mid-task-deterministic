"""
Instruction presentation: pages through a hardcoded list of instruction pages
via the shared psyexp_core instruction pager, then waits for the start key.

Each page is text plus an optional cue shape drawn beneath it as a visual aid,
so the pages that describe CIRCLE / SQUARE cues also show the shape. The task
owns the pages and how each is drawn; the harness owns the flip + key-polling
navigation loop.
"""
from __future__ import annotations

from dataclasses import dataclass

from psychopy import visual
from psychopy.hardware import keyboard
from psyexp_core import instructions as core_instructions
from psyexp_core.keyboard import get_keys
from rich.console import Console

from mid_det import config
from mid_det.task import display


@dataclass(frozen=True)
class InstructionPage:
    """One instruction page: prompt text and an optional example cue as a visual aid.

    ``cue`` is a ``(polarity, magnitude)`` pair drawn via ``display.draw_cue`` — the
    full cue (shape + magnitude chord + dollar label), matching what participants
    see on a real trial — or ``None`` for a text-only page.
    """
    text: str
    cue: tuple[str, int] | None = None


# The circle/square explanations are split one-shape-per-page so each page can
# show the cue it describes. An example cue is drawn with a representative
# high ($5) magnitude so the chord (magnitude line) is clearly off-center.
# Navigation / "press to continue" hints are drawn by the harness (instr_first),
# so they are not repeated in the text here.
_EXAMPLE_MAGNITUDE = 5

_PAGES: list[InstructionPage] = [
    InstructionPage(
        "In this experiment you will respond as quickly as possible to earn "
        "money. You will see a cue indicating how much money you can win or "
        "avoid losing. After this cue, a triangle will appear. Hit a button as "
        "fast as you can when the triangle appears to win."
    ),
    InstructionPage(
        "Cues are either circles or squares. CIRCLE cues mean that you can EARN "
        "that amount if you hit the target.",
        cue=("gain", _EXAMPLE_MAGNITUDE),
    ),
    InstructionPage(
        "SQUARE cues mean that you can AVOID LOSING that amount if you hit the "
        "target.",
        cue=("loss", _EXAMPLE_MAGNITUDE),
    ),
    InstructionPage(
        "If you miss a CIRCLE cue, you will NOT GAIN the amount shown in the cue.",
        cue=("gain", _EXAMPLE_MAGNITUDE),
    ),
    InstructionPage(
        "If you miss a SQUARE cue, you will LOSE the amount shown in the cue.",
        cue=("loss", _EXAMPLE_MAGNITUDE),
    ),
    InstructionPage("Please HOLD STILL while you are in the scanner."),
]

# On cue pages the prompt is raised so text clears the cue drawn at screen center,
# and the "press to continue" hint is lowered so it clears the dollar label drawn
# just below the cue. Plain pages keep the hint at its default position.
_PROMPT_Y_PLAIN = 0.1
_PROMPT_Y_WITH_CUE = 0.3
_HINT_Y_WITH_CUE = -0.35


def display_instructions(
    win: visual.Window,
    stimuli,              # Stimuli dataclass from display.py; avoid circular import
    kb: keyboard.Keyboard,
    rcon: Console,
) -> None:
    """Display the hardcoded instruction pages one at a time."""
    default_hint_y = stimuli.instr_first.pos[1]

    def _draw_page(page: InstructionPage, _is_last: bool) -> None:
        stimuli.instr_prompt.pos = (
            0,
            _PROMPT_Y_WITH_CUE if page.cue else _PROMPT_Y_PLAIN,
        )
        stimuli.instr_prompt.text = page.text
        stimuli.instr_prompt.draw()
        if page.cue:
            polarity, magnitude = page.cue
            display.draw_cue(stimuli, polarity, magnitude)
        stimuli.instr_first.pos = (
            0,
            _HINT_Y_WITH_CUE if page.cue else default_hint_y,
        )
        stimuli.instr_first.draw()

    core_instructions.page_through(
        win,
        _PAGES,
        _draw_page,
        forward_keys=config.INSTRUCTION_KEYS["forward"],
        back_keys=config.INSTRUCTION_KEYS["back"],
        quit_keys=config.QUIT_KEYS,
        kb=kb,
    )

    start_key = config.START_KEYS[0]
    rcon.print(
        f"[bold yellow]End of instructions — press '{start_key}' to continue...[/bold yellow]"
    )
    while True:
        stimuli.instr_finish.draw()
        win.flip()
        if get_keys(kb, config.START_KEYS):
            break
