"""
Session initialisation: dialog, screen setup, output directory, and instruction
display.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import platform
import statistics

import pyglet
from psychopy import core, monitors, visual
from psychopy.hardware import keyboard
from rich.console import Console

from mid_det import config

_PACKAGE_DIR = Path(__file__).parent          # src/mid_det/
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent    # project root
_TEXT_DIR = _PROJECT_ROOT / "text"


@dataclass
class SessionInfo:
    subject_id: str
    fmri: bool
    run_n: str                 # "1" | "2" | "practice"
    show_instructions: bool
    base_rt_s: float
    rt_change_s: float = config.RT_CHANGE_S   # staircase step; set by wizard
    legacy_name: str = ""                     # NAME for legacy-fmt/{NAME}_b{run}.csv


@dataclass
class ScreenDiagnostics:
    gl_vendor: str
    gl_renderer: str
    win_type: str
    pyglet_version: str
    platform_str: str
    calib_median_ms: float
    calib_p99_ms: float
    calib_max_ms: float
    calib_n: int


def setup_screen() -> tuple[list[int], visual.Window, ScreenDiagnostics]:
    display = pyglet.canvas.get_display()
    screens = display.get_screens()
    win_res = [screens[-1].width, screens[-1].height]
    exp_mon = monitors.Monitor("exp_mon")
    exp_mon.setSizePix(win_res)
    win = visual.Window(
        size=win_res,
        screen=len(screens) - 1,
        allowGUI=True,
        fullscr=True,
        monitor=exp_mon,
        units="height",
        color=(-1, -1, -1),
        waitBlanking=True,
    )

    # Explicitly enable VSYNC on the pyglet window.
    handle = getattr(win, "winHandle", None)
    if handle is not None and hasattr(handle, "set_vsync"):
        handle.set_vsync(True)

    # Collect backend identifiers so timing spikes can be correlated with
    # driver/compositor in post-hoc analysis.
    try:
        gl_info = pyglet.gl.current_context.get_info()
        gl_vendor = gl_info.get_vendor()
        gl_renderer = gl_info.get_renderer()
    except Exception:  # noqa: BLE001 — diagnostic only
        gl_vendor = "?"
        gl_renderer = "?"

    # VSYNC calibration: flip ~120 times and measure intervals. If the 99th
    # percentile is well above one frame period, vsync is not actually blocking
    # — typical on Windows under DWM composition or borderless fullscreen.
    intervals_ms: list[float] = []
    # Warm-up flips before measurement: PsychoPy's detectingFrameDrops doc notes
    # drops are common during startup as the GPU/driver/compositor settle. Run
    # these before the calibration loop so the median feeding frame_dur_s is
    # measured on a settled context, not a cold one.
    for _ in range(30):
        win.flip()
    last_t = core.getTime()
    for _ in range(120):
        win.flip()
        now = core.getTime()
        intervals_ms.append((now - last_t) * 1000)
        last_t = now
    intervals_ms.sort()
    median = statistics.median(intervals_ms)
    p99 = intervals_ms[int(0.99 * len(intervals_ms)) - 1]
    mx = intervals_ms[-1]

    # Enable PsychoPy's frame interval recording so trial.run_response can read
    # win.nDroppedFrames and isolate on-screen drops from measurement artifacts.
    win.refreshThreshold = (median / 1000.0) * 1.5
    win.recordFrameIntervals = True

    diagnostics = ScreenDiagnostics(
        gl_vendor=gl_vendor,
        gl_renderer=gl_renderer,
        win_type=str(getattr(win, "winType", "?")),
        pyglet_version=str(getattr(pyglet, "version", "?")),
        platform_str=platform.platform(),
        calib_median_ms=round(median, 3),
        calib_p99_ms=round(p99, 3),
        calib_max_ms=round(mx, 3),
        calib_n=len(intervals_ms),
    )

    return win_res, win, diagnostics


def make_run_dir(data_dir: Path, session_info: SessionInfo, session_time: datetime) -> Path:
    ts = session_time.strftime("%Y%m%dT%H%M%S")
    run_dir = data_dir / f"{session_info.subject_id}_run{session_info.run_n}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def display_instructions(
    win: visual.Window,
    stimuli,              # Stimuli dataclass from display.py; avoid circular import
    session_info: SessionInfo,
    kb: keyboard.Keyboard,
    rcon: Console,
) -> None:
    """Display instructions from text/instructions_MID.txt one page at a time."""
    keys_map = config.KEYS_FMRI if session_info.fmri else config.KEYS_BEHAVIORAL
    forward_key = keys_map["forward"]
    start_key = keys_map["start"]
    end_key = keys_map["end"]

    inst_path = _TEXT_DIR / "instructions_MID.txt"
    pages: list[str] = []
    with open(inst_path) as f:
        for line in f:
            stripped = line.rstrip()
            if stripped:
                pages.append(stripped)

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
