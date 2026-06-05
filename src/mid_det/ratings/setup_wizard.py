"""
Trimmed interactive setup wizard for the cue-ratings survey.

Reuses the styling and quit helpers from mid_det.setup_wizard; prompts only for
Subject ID and whether to show instructions (no fmri/run/timing fields).
"""
from __future__ import annotations

from pathlib import Path

import questionary
from prompt_toolkit.formatted_text import HTML
from rich.panel import Panel
from rich.text import Text

from mid_det.setup_wizard import (
    _QSTYLE,
    _SUBJECT_PLACEHOLDER,
    _quit,
    _rcon,
    prompt_legacy_name,
)

# Project root: src/mid_det/ratings/wizard.py -> project root (matches __main__).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def run_ratings_wizard() -> tuple[str, bool, str]:
    """Return (subject_id, show_instructions, legacy_name)."""
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

    # Placeholder (not a default): shown greyed-out so production users type the
    # real ID without clearing a field. Pressing Enter on an empty field falls
    # back to the placeholder value — convenient for testing.
    subject_id: str | None = questionary.text(
        "Subject ID",
        placeholder=HTML(f"<placeholder>{_SUBJECT_PLACEHOLDER}</placeholder>"),
        style=_QSTYLE,
    ).ask()
    if subject_id is None:
        _quit()
    subject_id: str = subject_id.strip() or _SUBJECT_PLACEHOLDER

    show_instructions: bool | None = questionary.confirm(
        "Show instructions?", default=True, style=_QSTYLE
    ).ask()
    if show_instructions is None:
        _quit()

    legacy_name = prompt_legacy_name(
        _PROJECT_ROOT / "data" / "legacy-fmt",
        lambda n: f"{n}_ratings.csv",
    )

    return subject_id, show_instructions, legacy_name
