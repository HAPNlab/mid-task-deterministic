"""
Trimmed interactive setup wizard for the cue-ratings survey.

Built on the shared psyexp_core.wizard primitives; prompts only for Subject ID
and whether to show instructions (no fmri/run/timing fields).
"""
from __future__ import annotations

from pathlib import Path

from psyexp_core import wizard
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from mid_det.io.setup_wizard import _SUBJECT_PLACEHOLDER

_rcon = Console(stderr=True)

# Project root: src/mid_det/ratings/setup_wizard.py -> project root (matches __main__).
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
    subject_id = wizard.ask_text("Subject ID", placeholder=_SUBJECT_PLACEHOLDER)
    subject_id_str = subject_id.strip() or _SUBJECT_PLACEHOLDER

    show_instructions = wizard.ask_confirm("Show instructions?", default=True)

    legacy_name = wizard.prompt_unique_name(
        "Legacy filename",
        _PROJECT_ROOT / "data" / "legacy-fmt",
        lambda n: f"{n}_ratings.csv",
    )

    return subject_id_str, show_instructions, legacy_name
