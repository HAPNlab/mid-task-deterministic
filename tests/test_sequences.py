"""
Sequence file invariants — expected values derived from MATLAB main.m.

main.m hard-codes:
  cues_b1      (42 entries, 7 of each of 6 cue types)
  cues_b2      (48 entries, 8 of each cue type)
  cues_practice(12 entries, 2 of each cue type)

  itis_b1      (42 entries: 14 × 2 s, 14 × 4 s, 14 × 6 s)
  itis_b2      (48 entries: 16 × 2 s, 16 × 4 s, 16 × 6 s)
  itis_practice(12 entries:  4 × 2 s,  4 × 4 s,  4 × 6 s)

ITIs stored in TR units (TR = 2 s):  n_iti ∈ {1, 2, 3}.
"""
from __future__ import annotations

import pytest

from mid_det import config
from mid_det.sequences import load_sequence


# ── schema ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("run_n", ["1", "2", "practice"])
def test_required_columns_present(run_n):
    df = load_sequence(run_n)
    assert {"valence", "magnitude", "n_iti"}.issubset(df.columns)


@pytest.mark.parametrize("run_n", ["1", "2", "practice"])
def test_valence_and_magnitude_values_valid(run_n):
    df = load_sequence(run_n)
    assert df["valence"].isin(config.VALENCES).all()
    assert df["magnitude"].isin(config.MAGNITUDES).all()


# ── trial counts (main.m cues_b* arrays) ─────────────────────────────────────

@pytest.mark.parametrize("run_n,expected_total,per_cue", [
    ("1",        42, 7),
    ("2",        48, 8),
    ("practice", 12, 2),
])
def test_trial_count_and_cue_balance(run_n, expected_total, per_cue):
    """
    Total trials and per-cue counts must match MATLAB main.m cues arrays.
    Each of the 6 cue types (2 valences × 3 magnitudes) appears equally often.
    """
    df = load_sequence(run_n)
    assert len(df) == expected_total, (
        f"run={run_n}: expected {expected_total} trials, got {len(df)}"
    )
    counts = df.groupby(["valence", "magnitude"]).size()
    for valence in config.VALENCES:
        for mag in config.MAGNITUDES:
            n = counts.get((valence, mag), 0)
            assert n == per_cue, (
                f"run={run_n}: cue ({valence},{mag}) appears {n} times, "
                f"expected {per_cue}"
            )


# ── ITI balance (main.m itis_b* arrays) ──────────────────────────────────────

@pytest.mark.parametrize("run_n,expected_per_duration", [
    ("1",        14),
    ("2",        16),
    ("practice",  4),
])
def test_iti_balance(run_n, expected_per_duration):
    """
    MATLAB itis arrays are perfectly balanced across 2 s / 4 s / 6 s.
    In TR units: equal counts of n_iti = 1, 2, 3.
    """
    df = load_sequence(run_n)
    for n_iti_val in [1, 2, 3]:
        count = (df["n_iti"] == n_iti_val).sum()
        assert count == expected_per_duration, (
            f"run={run_n}: n_iti={n_iti_val} appears {count} times, "
            f"expected {expected_per_duration}"
        )


@pytest.mark.parametrize("run_n", ["1", "2", "practice"])
def test_no_unexpected_iti_values(run_n):
    """n_iti must be exactly 1, 2, or 3 (= 2 s, 4 s, 6 s from MATLAB)."""
    df = load_sequence(run_n)
    unexpected = set(df["n_iti"].unique()) - {1, 2, 3}
    assert not unexpected, (
        f"run={run_n}: unexpected n_iti values {unexpected}"
    )

def test_sequences_order():
    """checks whether the sequences spreadsheets were copied correctly from the Matlab task."""

    # These variables below were copied straight from the Matlab codebase
    runs = {
        "1": {
            "cues": [1, 2, 2, 4, 4, 6, 4, 4, 3, 2, 5, 1, 5, 5, 6, 3, 4, 2, 1, 2, 6, 3, 6, 5, 3, 2, 5,
                     1, 5, 6, 1, 4, 2, 4, 6, 1, 6, 3, 5, 3, 3, 1],
            "seconds_iti": [6, 6, 6, 2, 4, 4, 6, 4, 6, 4, 6, 2, 2, 6, 2, 4, 4, 6, 2, 4, 6, 6, 4, 2, 4, 6, 4,
                            2, 2, 6, 6, 6, 2, 2, 4, 4, 2, 4, 2, 2, 2, 4]
        },
        "2": {
            "cues": [4, 2, 5, 1, 6, 2, 4, 1, 4, 3, 2, 6, 2, 4, 3, 2, 3, 3, 6, 6, 3, 2, 1, 3, 4, 5, 2,
                     5, 1, 5, 6, 5, 3, 3, 6, 5, 5, 2, 1, 6, 4, 4, 1, 4, 5, 1, 1, 6],
            "seconds_iti": [6, 4, 2, 2, 4, 4, 6, 2, 2, 6, 6, 4, 6, 4, 2, 6, 2, 6, 4, 6, 2, 6, 6, 4, 2, 4, 6,
                            2, 6, 2, 4, 6, 6, 4, 2, 4, 4, 4, 2, 4, 4, 4, 6, 2, 6, 2, 2, 2]
        },
        "practice": {
            "cues": [3, 4, 6, 1, 3, 2, 5, 5, 1, 6, 2, 4],
            "seconds_iti": [2, 4, 2, 4, 2, 6, 6, 4, 4, 2, 6, 6]
        }
    }

    cues_conversion = {
        1: ("loss", 0),
        2: ("loss", 1),
        3: ("loss", 5),
        4: ("gain", 0),
        5: ("gain", 1),
        6: ("gain", 5)
    }

    for run_name, run_spec in runs.items():
        expected_sequence = []

        for cue_raw, seconds_iti in zip(run_spec["cues"], run_spec["seconds_iti"]):
            valence, magnitude = cues_conversion[cue_raw]

            expected_sequence.append({
                "valence": valence,
                "magnitude": magnitude,
                "n_iti": seconds_iti // 2,
            })

        actual_sequence = load_sequence(run_name).to_dict("records")
        assert actual_sequence == expected_sequence
