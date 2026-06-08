"""Sequence CSV loading and validation."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from mid_det import config

_PROJECT_ROOT = Path(__file__).resolve().parents[3]   # src/mid_det/io/ -> project root
_SEQUENCES_DIR = _PROJECT_ROOT / "sequences"


def load_sequence(run_n: str) -> pd.DataFrame:
    """Read sequences/{run_n}.csv and return a validated DataFrame."""
    if run_n == "practice":
        path = _SEQUENCES_DIR / "practice.csv"
    else:
        path = _SEQUENCES_DIR / f"run_{run_n}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Sequence file not found: {path}")
    df = pd.read_csv(path)
    required = {"polarity", "magnitude", "n_iti"}
    if not required.issubset(df.columns):
        raise ValueError(f"Sequence file must have columns {required}; got {set(df.columns)}")
    df["magnitude"] = df["magnitude"].astype(int)
    df["n_iti"] = df["n_iti"].astype(int)
    df["polarity"] = df["polarity"].astype(str)

    for i, row in df.iterrows():
        if row["polarity"] not in config.POLARITIES:
            raise ValueError(f"row {i}: polarity '{row['polarity']}' not in {config.POLARITIES}")
        if int(row["magnitude"]) not in config.MAGNITUDES:
            raise ValueError(f"row {i}: magnitude '{row['magnitude']}' not in {config.MAGNITUDES}")
        pair = (row["polarity"], int(row["magnitude"]))
        if pair not in config.TRIAL_TYPE_MAP:
            raise ValueError(
                f"row {i}: (polarity, magnitude) {pair} has no trial type in "
                f"config.TRIAL_TYPE_MAP"
            )

    return df.reset_index(drop=True)
