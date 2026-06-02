"""
Trimmed interactive setup wizard for the cue-ratings survey.

Reuses the styling and quit helpers from mid_det.setup_wizard; prompts only for
Subject ID and whether to show instructions (no fmri/run/timing fields).
"""
from __future__ import annotations

import questionary
from rich.panel import Panel
from rich.text import Text

from mid_det.setup_wizard import _QSTYLE, _quit, _rcon


def run_ratings_wizard() -> tuple[str, bool]:
    """Return (subject_id, show_instructions)."""
    _rcon.print()
    _rcon.print(
        Panel(
            Text(
                "MID Cue-Ratings Survey — Setup",
                style="bold white",
                justify="center",
            ),
            border_style="bright_blue",
            padding=(0, 4),
        )
    )
    _rcon.print()

    subject_id: str | None = questionary.text(
        "Subject ID", default="XXX000", style=_QSTYLE
    ).ask()
    if subject_id is None:
        _quit()

    show_instructions: bool | None = questionary.confirm(
        "Show instructions?", default=True, style=_QSTYLE
    ).ask()
    if show_instructions is None:
        _quit()

    return subject_id, show_instructions
