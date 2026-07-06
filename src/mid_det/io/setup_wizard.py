"""
Interactive terminal setup wizard for the MID task.

Replaces the PsychoPy gui.DlgFromDict dialog with a questionary/prompt_toolkit
wizard built on the shared psyexp_core.wizard primitives (styles, ask_* helpers,
the overwrite-guarded filename prompt, and quit handling). The MID-specific bits
stay here: a frame-stepping RT prompt that

  - defaults RT fields to frame-aligned values,
  - lets operators step RT values with ↑/↓ arrows (±1 frame each press), and
  - shows a live "≈ X frames" bottom-toolbar so any entered value is grounded
    in display timing.
"""
from __future__ import annotations

from pathlib import Path

import questionary
from prompt_toolkit import prompt as _pt_prompt
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.validation import ValidationError, Validator
from psyexp_core import wizard
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from mid_det import config
from mid_det.io.bootstrap import SessionInfo

_rcon = Console(stderr=True)

# Placeholder subject ID — shown greyed-out and used as the fallback when the
# field is left empty (handy for testing).
_SUBJECT_PLACEHOLDER = "XXX000"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _frame_multiples(frame_dur_ms: float, n: int = 5) -> list[float]:
    """Return the first *n* multiples of frame_dur_ms, rounded to 2 dp."""
    return [round(frame_dur_ms * i, 2) for i in range(1, n + 1)]


def _nearest_frame_aligned(value_ms: float, frame_dur_ms: float) -> float:
    """Round value_ms to the nearest whole-frame multiple."""
    return round(round(value_ms / frame_dur_ms) * frame_dur_ms, 2)


# ── Custom RT field ───────────────────────────────────────────────────────────


class _RTMaxValidator(Validator):
    """Positive-float validator with an upper-bound check (in ms)."""

    def __init__(self, max_ms: float, response_ms: float, jitter_max_ms: float):
        self.max_ms = max_ms
        self.response_ms = response_ms
        self.jitter_max_ms = jitter_max_ms

    def validate(self, document):
        text = document.text.strip()
        try:
            v = float(text)
        except ValueError:
            raise ValidationError(
                message="Enter a number (ms)", cursor_position=len(text)
            )
        if v <= 0:
            raise ValidationError(
                message="Value must be > 0 ms", cursor_position=len(text)
            )
        if v > self.max_ms:
            raise ValidationError(
                message=(
                    f"Must be ≤ {self.max_ms:.0f} ms "
                    f"(response phase {self.response_ms:.0f} ms "
                    f"− max jitter {self.jitter_max_ms:.0f} ms)"
                ),
                cursor_position=len(text),
            )


def _rt_prompt(
    label: str,
    default_ms: float,
    frame_dur_ms: float,
    max_ms: float | None = None,
    response_ms: float | None = None,
    jitter_max_ms: float | None = None,
) -> float:
    """
    Interactive prompt for an RT value in milliseconds.

    - ↑/↓ arrows step the value by ±1 frame
    - Typing allows any positive number
    - Bottom toolbar shows live frame-count (green if frame-aligned, yellow if not)
    """
    # Print label + hint line above the input field
    _rcon.print(
        f"  [bold #5f819d]?[/bold #5f819d] [bold]{label}[/bold]  "
        f"[dim]↑/↓ = ±{frame_dur_ms:.2f} ms (1 frame)[/dim]",
        highlight=False,
    )
    hints = _frame_multiples(frame_dur_ms)
    hint_str = "  ".join(
        f"[cyan]{v:.2f}[/cyan][dim]({i + 1}fr)[/dim]"
        for i, v in enumerate(hints)
    )
    _rcon.print(f"  [dim]Hints:[/dim] {hint_str}", highlight=False)

    # Key bindings: ↑/↓ step the buffer by one frame
    kb = KeyBindings()

    @kb.add("up")
    def _up(event):
        buf = event.app.current_buffer
        try:
            v = float(buf.text)
        except ValueError:
            v = default_ms
        new_v = max(frame_dur_ms, round(v + frame_dur_ms, 2))
        buf.text = f"{new_v:.2f}"
        buf.cursor_position = len(buf.text)

    @kb.add("down")
    def _down(event):
        buf = event.app.current_buffer
        try:
            v = float(buf.text)
        except ValueError:
            v = default_ms
        new_v = max(frame_dur_ms, round(v - frame_dur_ms, 2))
        buf.text = f"{new_v:.2f}"
        buf.cursor_position = len(buf.text)

    # Bottom toolbar: live frame-count feedback
    def _toolbar():
        try:
            text = get_app().current_buffer.text
            v = float(text)
        except Exception:
            return HTML("<b> Enter a positive number</b>")
        if v <= 0:
            return HTML("<ansired><b> ✗  Must be > 0 ms</b></ansired>")
        if max_ms is not None and v > max_ms:
            return HTML(
                f"<ansired><b> ✗  Must be ≤ {max_ms:.0f} ms</b></ansired>"
            )
        frames = v / frame_dur_ms
        n = int(round(frames))
        if abs(frames - n) < 0.01:
            plural = "frame" if n == 1 else "frames"
            return HTML(f"<ansigreen><b> = {n} {plural} ✓</b></ansigreen>")
        else:
            return HTML(f"<ansiyellow><b> ≈ {frames:.2f} frames</b></ansiyellow>")

    if max_ms is not None:
        validator: Validator = _RTMaxValidator(
            max_ms=max_ms,
            response_ms=response_ms if response_ms is not None else 0.0,
            jitter_max_ms=jitter_max_ms if jitter_max_ms is not None else 0.0,
        )
    else:
        validator = wizard.PosFloatValidator(unit="ms")

    try:
        raw = _pt_prompt(
            FormattedText([("class:prompt", "  ❯ ")]),
            default=f"{default_ms:.2f}",
            key_bindings=kb,
            bottom_toolbar=_toolbar,
            validator=validator,
            validate_while_typing=False,
            style=wizard.PT_STYLE,
        )
    except (KeyboardInterrupt, EOFError):
        wizard.quit_app()
    return float(raw)


# ── Main wizard ───────────────────────────────────────────────────────────────


def run_wizard(frame_dur_s: float) -> SessionInfo:
    """
    Run the interactive setup wizard and return a populated SessionInfo.

    *frame_dur_s* is the measured (or overridden) frame duration — it drives
    the default RT step size and the frame-alignment hints.
    """
    frame_dur_ms = frame_dur_s * 1000.0

    # ── Header ────────────────────────────────────────────────────────────────
    _rcon.print()
    _rcon.print(
        Panel(
            Text(
                "MID Task (Deterministic) — Setup",
                style="bold white",
                justify="center",
            ),
            border_style="bright_blue",
            padding=(0, 4),
        )
    )
    _rcon.print()

    # ── Session fields ────────────────────────────────────────────────────────
    # Placeholder (not a default): shown greyed-out so production users type the
    # real ID without having to clear the default value. Pressing Enter on an
    # empty field falls back to the placeholder value — convenient for testing.
    subject_id = wizard.ask_text("Subject ID", placeholder=_SUBJECT_PLACEHOLDER)
    subject_id_str = subject_id.strip() or _SUBJECT_PLACEHOLDER

    run_n: str = wizard.ask_select(
        "Task",
        choices=[
            questionary.Choice("Practice run", value="practice"),
            questionary.Choice("Run 1", value="1"),
            questionary.Choice("Run 2", value="2"),
        ],
    )

    fmri = wizard.ask_confirm("fMRI session?", default=False)
    show_instructions = wizard.ask_confirm("Show instructions?", default=True)

    # ── Legacy-format filename ────────────────────────────────────────────────
    legacy_name = wizard.prompt_unique_name(
        "Legacy filename",
        Path("data") / "legacy-fmt",
        lambda n: f"{n}_b{run_n}.csv",
    )

    # ── Timing fields ─────────────────────────────────────────────────────────
    _rcon.print()
    _rcon.print(Rule("[dim]Timing[/dim]", style="dim"))
    _rcon.print()

    # Baseline RT: default = nearest frame-aligned value to config BASE_RT_S.
    # Bounded above by (response phase − max jitter) so the full target window
    # can render on every trial regardless of jitter draw.
    config_base_ms = (
        config.BASE_RT_PRACTICE_S if run_n == "practice" else config.BASE_RT_S
    ) * 1000.0
    default_base_ms = _nearest_frame_aligned(config_base_ms, frame_dur_ms)
    response_ms = config.STUDY_TIMES_S["response"] * 1000.0
    jitter_max_ms = config.JITTER_MAX_S * 1000.0
    max_target_ms = response_ms - jitter_max_ms
    base_rt_ms = _rt_prompt(
        "Baseline RT",
        default_ms=default_base_ms,
        frame_dur_ms=frame_dur_ms,
        max_ms=max_target_ms,
        response_ms=response_ms,
        jitter_max_ms=jitter_max_ms,
    )

    _rcon.print()

    # RT step size: default = exactly 1 frame
    rt_change_ms = _rt_prompt(
        "RT step size",
        default_ms=round(frame_dur_ms, 2),
        frame_dur_ms=frame_dur_ms,
    )

    _rcon.print()

    return SessionInfo(
        subject_id=subject_id_str,
        fmri=fmri,
        run_n=run_n,
        show_instructions=show_instructions,
        base_rt_s=base_rt_ms / 1000.0,
        rt_change_s=rt_change_ms / 1000.0,
        legacy_name=legacy_name,
    )
