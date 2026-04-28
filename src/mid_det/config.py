"""
All task constants. No imports from other mid_det modules.
All time values are in seconds unless the name includes a unit suffix.
"""

# Phase durations (seconds)
STUDY_TIMES_S: dict[str, float] = {
    "cue": 2.0,
    "fixation": 2.0,
    "response": 2.0,
    "outcome": 2.0,
    "iti": 2.0,
}

# Valence → shape (and reward sign)
VALENCES: list[str] = ["gain", "loss"]
VALENCE_SHAPE: dict[str, str] = {"gain": "circle", "loss": "square"}
VALENCE_SIGN: dict[str, int] = {"gain": +1, "loss": -1}

# Magnitude tiers (absolute dollar amounts)
MAGNITUDES: list[int] = [0, 1, 5]

# Trial type lookup: 6 cue types, matching MATLAB mid-task `var.cues` indexing.
# 1 = low square (-$0), 2 = mid square (-$1), 3 = high square (-$5),
# 4 = low circle (+$0), 5 = mid circle (+$1), 6 = high circle (+$5).
TRIAL_TYPE_MAP: dict[tuple[str, int], int] = {
    ("loss", 0): 1,
    ("loss", 1): 2,
    ("loss", 5): 3,
    ("gain", 0): 4,
    ("gain", 1): 5,
    ("gain", 5): 6,
}

# Adaptive target-window staircase (per-cue), matching MATLAB PresentTarget.m.
# Target duration starts at BASE_RT_S for each cue type and adjusts by
# RT_CHANGE_S each trial once the cue has at least MIN_TRIALS_FOR_ADAPT prior
# trials: cumulative win-ratio > WIN_RATIO_THRESHOLD shrinks the window
# (harder), otherwise grows it (easier).
BASE_RT_S: float = 0.265
BASE_RT_PRACTICE_S: float = 0.400
RT_CHANGE_S: float = 0.020
WIN_RATIO_THRESHOLD: float = 0.66
MIN_TRIALS_FOR_ADAPT: int = 3

# Run structure (matches MATLAB var.leadin / var.leadout for scanned blocks).
INITIAL_FIX_DUR_S: float = 12.0
CLOSING_FIX_DUR_S: float = 8.0
# Practice block uses shortened leadin/leadout (MATLAB main.m lines 154-155).
PRACTICE_INITIAL_FIX_DUR_S: float = 2.0
PRACTICE_CLOSING_FIX_DUR_S: float = 0.0

# Pre-target jitter from response-phase onset to target onset.
# Matches MATLAB front-buffer timing: 0.25 + rand()*0.75 seconds.
JITTER_MIN_S: float = 0.25
JITTER_MAX_S: float = 1.0

# Scanner settings
SCANNER_PULSE_RATE: int = 46
BOARD_NUM: int = 0
MR_SETTINGS: dict = {
    "TR": 2.0,
    "volumes": 356,
    "sync": "equal",
    "skip": 0,
    "sound": False,
}

# Keyboard layouts
KEYS_FMRI: dict[str, str] = {"forward": "7", "back": "6", "start": "0", "end": "l"}
KEYS_BEHAVIORAL: dict[str, str] = {"forward": "4", "back": "3", "start": "0", "end": "l"}
EXP_KEYS: list[str] = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


def cue_label(valence: str, magnitude: int) -> str:
    """Return the on-screen dollar label for a (valence, magnitude) cue."""
    sign = "+" if VALENCE_SIGN[valence] > 0 else "-"
    return f"{sign}${magnitude}.00"
