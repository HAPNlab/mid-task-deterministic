"""
Session initialisation: dialog, screen setup, output directory, sequence loading,
and instruction display.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyglet
from psychopy import core, event as psy_event, gui, monitors, visual

from mid_det import config

_PACKAGE_DIR = Path(__file__).parent          # src/mid_det/
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent    # project root
_SEQUENCES_DIR = _PROJECT_ROOT / "sequences"
_TEXT_DIR = _PROJECT_ROOT / "text"


@dataclass
class SessionInfo:
    subject_id: str
    fmri: bool
    run_n: str                 # "1" | "2" | "practice"
    show_instructions: bool
    base_rt_s: float


def show_dialog() -> SessionInfo:
    """Present the startup dialog and return a SessionInfo."""
    default_base_rt_ms = int(round(config.BASE_RT_S * 1000.0))
    fields = {
        "Subject ID": "XXX000",
        "fMRI? (yes/no)": "no",
        "Task number (1/2/practice)": "practice",
        "Show instructions? (yes/no)": "yes",
        "Baseline RT (ms; 250-280 typical, 400 for practice)": str(default_base_rt_ms),
    }
    while True:
        dlg = gui.DlgFromDict(dictionary=fields, title="MID Task (Deterministic)")
        if not dlg.OK:
            core.quit()

        run_n = str(fields["Task number (1/2/practice)"]).strip()
        base_rt_ms_raw = str(fields["Baseline RT (ms; 250-280 typical, 400 for practice)"]).strip()
        try:
            base_rt_ms = float(base_rt_ms_raw)
        except ValueError:
            gui.warnDlg(prompt=f"Baseline RT must be a number (got '{base_rt_ms_raw}').")
            continue
        if base_rt_ms <= 0:
            gui.warnDlg(prompt=f"Baseline RT must be > 0 ms (got {base_rt_ms}).")
            continue
        break

    return SessionInfo(
        subject_id=str(fields["Subject ID"]),
        fmri=fields["fMRI? (yes/no)"].strip().lower() == "yes",
        run_n=run_n,
        show_instructions=fields["Show instructions? (yes/no)"].strip().lower() == "yes",
        base_rt_s=base_rt_ms / 1000.0,
    )


def setup_screen() -> tuple[list[int], visual.Window]:
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
    )
    return win_res, win


def make_run_dir(data_dir: Path, session_info: SessionInfo, session_time: datetime) -> Path:
    ts = session_time.strftime("%Y%m%dT%H%M%S")
    run_dir = data_dir / f"{session_info.subject_id}_run{session_info.run_n}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_sequence(run_n: str) -> pd.DataFrame:
    """Read sequences/{run_n}.csv and return a validated DataFrame."""
    if run_n == "practice":
        path = _SEQUENCES_DIR / "practice.csv"
    else:
        path = _SEQUENCES_DIR / f"run_{run_n}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Sequence file not found: {path}")
    df = pd.read_csv(path)
    required = {"valence", "magnitude", "n_iti"}
    if not required.issubset(df.columns):
        raise ValueError(f"Sequence file must have columns {required}; got {set(df.columns)}")
    df["magnitude"] = df["magnitude"].astype(int)
    df["n_iti"] = df["n_iti"].astype(int)
    df["valence"] = df["valence"].astype(str)

    # Validate values
    for i, row in df.iterrows():
        if row["valence"] not in config.VALENCES:
            raise ValueError(f"row {i}: valence '{row['valence']}' not in {config.VALENCES}")
        if int(row["magnitude"]) not in config.MAGNITUDES:
            raise ValueError(f"row {i}: magnitude '{row['magnitude']}' not in {config.MAGNITUDES}")

    return df.reset_index(drop=True)


def display_instructions(
    win: visual.Window,
    stimuli,              # Stimuli dataclass from display.py; avoid circular import
    session_info: SessionInfo,
) -> None:
    """Display instructions from text/instructions_MID.txt one page at a time."""
    keys_map = config.KEYS_FMRI if session_info.fmri else config.KEYS_BEHAVIORAL
    forward_key = keys_map["forward"]
    back_key = keys_map["back"]
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

    psy_event.clearEvents()
    page_idx = 0

    while True:
        stimuli.instr_prompt.text = pages[page_idx]
        stimuli.instr_prompt.draw()
        if page_idx == 0:
            stimuli.instr_first.draw()
        else:
            stimuli.instr_move.draw()
        win.flip()

        pressed = psy_event.getKeys(keyList=[forward_key, back_key, end_key])
        if not pressed:
            continue
        key_name = pressed[0]
        if key_name == end_key:
            core.quit()
        elif key_name == back_key and page_idx > 0:
            page_idx -= 1
        elif key_name == forward_key:
            page_idx += 1
            if page_idx >= len(pages):
                break

    while True:
        stimuli.instr_finish.draw()
        win.flip()
        if psy_event.getKeys(keyList=[start_key]):
            break
