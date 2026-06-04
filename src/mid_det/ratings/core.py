"""
Pure logic for the cue-ratings survey — no PsychoPy, no I/O side effects beyond
the explicit CSV writer. Kept import-light so it is unit-testable without a
display.

Ported from MATLAB RunRatings.m / ParseData.m.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

# 7-point scale (MATLAB c.numEls = 7).
N_ELS: int = 7

# Slider start positions. Both scales start at the middle (round(numEls/2) = 4).
START_SLIDEPOS: dict[str, int] = {"valence": 4, "arousal": 4}


@dataclass(frozen=True)
class RatingCue:
    """One cue to be rated, identified by its polarity + magnitude.

    ``polarity`` is the MID gain/loss dimension (shape); not to be confused with
    the affective *valence* the participant rates on this cue (1-7).
    """
    idx: int          # MATLAB 1..6 ordering
    polarity: str     # "loss" | "gain"  -> square | circle
    magnitude: int    # 0 | 1 | 5


# Canonical MATLAB order (RunRatings.m var.cues = [1..6]).
# square = loss, circle = gain; magnitude 0/1/5.
RATING_CUES: list[RatingCue] = [
    RatingCue(1, "loss", 0),
    RatingCue(2, "loss", 1),
    RatingCue(3, "loss", 5),
    RatingCue(4, "gain", 0),
    RatingCue(5, "gain", 1),
    RatingCue(6, "gain", 5),
]


# Scale colors, MATLAB 0-255 RGB (RunRatings.m greenColors / twoColors).
# valence: blue (very negative) -> beige (neutral) -> orange (very positive)
VALENCE_COLORS_255: list[tuple[int, int, int]] = [
    (0, 0, 255),
    (50, 50, 255),
    (100, 100, 255),
    (245, 245, 220),
    (245, 165, 79),
    (255, 150, 50),
    (255, 100, 50),
]
# arousal: pale green (very low) -> saturated green (very high)
AROUSAL_COLORS_255: list[tuple[int, int, int]] = [
    (250, 255, 250),
    (200, 255, 200),
    (150, 255, 150),
    (100, 255, 100),
    (50, 255, 50),
    (25, 255, 25),
    (0, 200, 0),
]

# Scale legend text (3 anchors) and title, per RunRatings.m.
SCALE_TITLES: dict[str, str] = {"valence": "VALENCE", "arousal": "AROUSAL"}
SCALE_LEGENDS: dict[str, tuple[str, str, str]] = {
    "valence": ("Very Negative", "Neutral", "Very Positive"),
    "arousal": ("Very Low", "Moderate", "Very High"),
}


def clamp_slider(pos: int, delta: int, n_els: int = N_ELS) -> int:
    """Apply a ±1 slider move and clamp to [1, n_els]."""
    return max(1, min(n_els, pos + delta))


CSV_HEADER: list[str] = ["polarity", "magnitude", "arousal", "valence"]


def build_csv_rows(results: list[dict]) -> list[list[str]]:
    """Build CSV rows (header + one per result) from a list of
    {'polarity': str, 'magnitude': int, 'arousal': int, 'valence': int} dicts.

    The cue is described by separate ``polarity`` and ``magnitude`` columns;
    ``arousal`` and ``valence`` are the 1-7 ratings (MATLAB ParseData.m order).
    """
    rows: list[list[str]] = [list(CSV_HEADER)]
    for r in results:
        rows.append([str(r[k]) for k in CSV_HEADER])
    return rows


def write_ratings_csv(path: Path, results: list[dict]) -> None:
    """Write the ratings CSV (polarity,magnitude,arousal,valence) to *path*."""
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(build_csv_rows(results))
