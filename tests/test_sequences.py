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
from mid_det.session import load_sequence


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
