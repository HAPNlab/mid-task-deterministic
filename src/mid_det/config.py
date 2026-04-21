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

# Difficulty levels and their FIXED target display durations (seconds).
# Replaces the QUEST staircase used in mid-task: target duration depends only
# on the trial's difficulty label, never on prior performance.
DIFFICULTIES: list[str] = ["low", "medium", "high"]
TARGET_DUR_S: dict[str, float] = {
    "low":    0.150,   # short  → harder
    "medium": 0.265,   # medium
    "high":   0.400,   # long   → easier
}

# Trial type lookup: (valence, magnitude, difficulty) -> integer 1-18
TRIAL_TYPE_MAP: dict[tuple[str, int, str], int] = {
    (valence, mag, diff): idx + 1
    for idx, (valence, mag, diff) in enumerate(
        (v, m, d) for v in VALENCES for m in MAGNITUDES for d in DIFFICULTIES
    )
}

# Run structure
INITIAL_FIX_DUR_S: float = 12.0
CLOSING_FIX_DUR_S: float = 8.0
JITTER_MAX_S: float = 0.05

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
    return f"{sign}${magnitude}"
