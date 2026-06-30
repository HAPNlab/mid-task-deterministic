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

# Nominal duration of the four fixed slides (cue+fixation+response+outcome) that
# precede the ITI. Used as the drift baseline, mirroring MATLAB main.m's hardcoded
# `- 8.0` (see trial.py timing_drift_ms).
PRE_ITI_NOMINAL_S: float = sum(
    STUDY_TIMES_S[k] for k in ("cue", "fixation", "response", "outcome")
)

# Polarity → shape (and reward sign). "polarity" is the gain/loss dimension;
# kept distinct from the affective "valence" rated in the cue-ratings survey.
POLARITIES: list[str] = ["gain", "loss"]
POLARITY_SHAPE: dict[str, str] = {"gain": "circle", "loss": "square"}
POLARITY_SIGN: dict[str, int] = {"gain": +1, "loss": -1}

# Magnitude tiers (absolute dollar amounts)
MAGNITUDES: list[int] = [0, 1, 5]

# Trial type lookup: 6 cue types, matching MATLAB mid-task `var.cues` indexing.
# Keys are (polarity, magnitude).
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
RT_CHANGE_S: float = 0.020          # fallback default; wizard sets it to 1 frame at runtime
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

# Plausible display refresh rates. Used to sanity-check measured/calibrated
# rates before we trust them for timing — anything outside this band is treated
# as a failed measurement rather than a real refresh rate.
MIN_REFRESH_HZ: float = 30.0
MAX_REFRESH_HZ: float = 200.0

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

# ── Keyboard bindings ─────────────────────────────────────────────────────────
# Standardized across HAPNlab PsychoPy tasks (cf. heat-task's config): every
# action maps to a *list* of accepted key names, and element [0] is the canonical
# key echoed on screen / in logs. Lists keep numpad and button-box variants
# ("num_1", "num_0") plus any alternates in one place, and reading them through
# the shared keyboard helpers (psyexp_core.keyboard.wait_for_key / check_quit)
# means escape-to-quit (QUIT_KEYS) is handled uniformly instead of hardcoded at
# each call site.
INSTRUCTION_KEYS: dict[str, list[str]] = {"forward": ["1", "num_1"], "back": []}
START_KEYS: list[str] = ["0", "num_0"]   # begin the run (non-fMRI; fMRI waits on the first TR)
END_KEYS: list[str] = ["0", "num_0"]     # dismiss the end screen / exit the run
QUIT_KEYS: list[str] = ["escape"]        # abort the run at any prompt
OVERLAY_TOGGLE_KEYS: list[str] = ["f3"]  # toggle the operator debug overlay

# Participant response keys for the target window (the button box reports the
# digit keys; kept separate from the operator/navigation bindings above).
RESPONSE_KEYS: list[str] = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


def cue_label(polarity: str, magnitude: int) -> str:
    """Return the on-screen dollar label for a (polarity, magnitude) cue."""
    sign = "+" if POLARITY_SIGN[polarity] > 0 else "-"
    return f"{sign}${magnitude}.00"
