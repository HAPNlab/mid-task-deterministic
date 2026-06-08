"""
Shared PsychoPy import shim.

Keeps the per-phase, response, and orchestration modules importable in
headless/CI environments without PsychoPy, so the pure-logic and timing code
stays testable. `core` is a namespace with the attributes those paths reference
— tests patch core.Clock; real runs always have PsychoPy.
"""
from __future__ import annotations

try:
    from psychopy import core, logging, visual
    from psychopy.hardware import keyboard
except ModuleNotFoundError:
    import types

    visual = keyboard = None  # type: ignore[assignment]
    logging = types.SimpleNamespace(exp=lambda *a, **k: None)  # type: ignore[assignment]
    core = types.SimpleNamespace(  # type: ignore[assignment]
        Clock=None, CountdownTimer=None, quit=lambda *a, **k: None
    )

__all__ = ["core", "logging", "visual", "keyboard"]
