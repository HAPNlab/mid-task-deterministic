"""Sequence CSV loading and validation."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from mid_det import config

_PACKAGE_DIR = Path(__file__).parent          # src/mid_det/
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent    # project root
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
    required = {"valence", "magnitude", "n_iti"}
    if not required.issubset(df.columns):
        raise ValueError(f"Sequence file must have columns {required}; got {set(df.columns)}")
    df["magnitude"] = df["magnitude"].astype(int)
    df["n_iti"] = df["n_iti"].astype(int)
    df["valence"] = df["valence"].astype(str)

    for i, row in df.iterrows():
        if row["valence"] not in config.VALENCES:
            raise ValueError(f"row {i}: valence '{row['valence']}' not in {config.VALENCES}")
        if int(row["magnitude"]) not in config.MAGNITUDES:
            raise ValueError(f"row {i}: magnitude '{row['magnitude']}' not in {config.MAGNITUDES}")

    return df.reset_index(drop=True)
