"""
Differential parity test: Python `CalibrationState` vs. the real MATLAB
staircase algorithm, executed through Octave (or MATLAB) as a reference engine.

Unlike `test_calibration.py` (which asserts against hand-derived numbers), this
feeds the *same* scripted win/loss sequences to both implementations and checks
the per-trial target windows match. The reference lives in
`tests/matlab_ref/calibration_ref.m`, extracted verbatim from
`MID-updated/scripts/PresentTarget.m` lines 14-48.

If neither `octave` nor `matlab` is on PATH, the parity tests skip — but a loud
warning is emitted so a green run never silently implies parity was verified.
"""
from __future__ import annotations

import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from mid_det import config
from mid_det.calibration import CalibrationState

_REF_DIR = Path(__file__).parent / "matlab_ref"

# cue id (1..6, as used by var.cues in MATLAB) -> (polarity, magnitude)
_CUE_TO_PM = {cue_id: pm for pm, cue_id in config.TRIAL_TYPE_MAP.items()}


# ── reference-engine discovery ────────────────────────────────────────────────

def _find_engine() -> tuple[str, str] | None:
    """Return (kind, executable_path) for octave or matlab, else None."""
    for kind in ("octave", "matlab"):
        path = shutil.which(kind)
        if path:
            return kind, path
    return None


_ENGINE = _find_engine()


@pytest.fixture(scope="session", autouse=True)
def _warn_if_no_engine():
    """Make a missing reference engine impossible to overlook in the summary."""
    if _ENGINE is None:
        warnings.warn(
            "calibration MATLAB-parity NOT verified — no Octave/MATLAB engine "
            "found on PATH; install octave (`brew install octave`) to run it.",
            stacklevel=2,
        )
    yield


requires_engine = pytest.mark.skipif(
    _ENGINE is None, reason="no octave/matlab engine on PATH (see emitted warning)"
)


# ── drivers ───────────────────────────────────────────────────────────────────

def _python_windows(
    cues: list[int], wins: list[int], base_rt: float, rt_change: float
) -> list[float]:
    """Per-trial target window from the Python implementation under test."""
    cal = CalibrationState(base_rt_s=base_rt, rt_change_s=rt_change)
    out: list[float] = []
    for cue_id, win in zip(cues, wins):
        polarity, magnitude = _CUE_TO_PM[cue_id]
        out.append(cal.next_target_dur_s(polarity, magnitude))
        cal.record_outcome(polarity, magnitude, bool(win))
    return out


def _octave_windows(
    cues: list[int], wins: list[int], base_rt: float, rt_change: float
) -> list[float]:
    """Per-trial target window from the MATLAB/Octave reference engine."""
    assert _ENGINE is not None
    kind, exe = _ENGINE
    cues_lit = " ".join(str(c) for c in cues)
    wins_lit = " ".join(str(w) for w in wins)
    # %.17g round-trips a double exactly; printf recycles the format per element.
    code = (
        f"addpath('{_REF_DIR}');"
        f"cv = calibration_ref([{cues_lit}], [{wins_lit}], {base_rt!r}, {rt_change!r});"
        f"printf('%.17g\\n', cv);"
    )
    cmd = [exe, "-batch", code] if kind == "matlab" else [exe, "--quiet", "--eval", code]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{kind} reference failed (rc={proc.returncode}):\n{proc.stderr}"
        )
    return [float(line) for line in proc.stdout.split() if line.strip()]


def _assert_parity(
    cues: list[int], wins: list[int], base_rt: float, rt_change: float
) -> list[float]:
    py = _python_windows(cues, wins, base_rt, rt_change)
    ref = _octave_windows(cues, wins, base_rt, rt_change)
    assert len(py) == len(cues)
    assert ref == pytest.approx(py, abs=1e-12)
    return py


# ── shared test data ──────────────────────────────────────────────────────────

def _random_sequence(seed: int, n: int) -> tuple[list[int], list[int]]:
    """Interleaved (cue, win) trials spanning all 6 cues, reproducible by seed."""
    import random

    rng = random.Random(seed)
    cue_ids = sorted(_CUE_TO_PM)
    cues = [rng.choice(cue_ids) for _ in range(n)]
    wins = [rng.randint(0, 1) for _ in range(n)]
    return cues, wins


# all-wins / all-misses runs on a single cue, plus the 0.66 boundary case
_ALL_WINS = ([5] * 8, [1] * 8)
_ALL_MISS = ([2] * 8, [0] * 8)
_BOUNDARY = ([4] * 51, [1] * 33 + [0] * 17 + [1])  # ratio hits exactly 33/50 = 0.66

_PARAMS = [(config.BASE_RT_S, config.RT_CHANGE_S), (config.BASE_RT_PRACTICE_S, 1 / 60.0)]


# ── tests ─────────────────────────────────────────────────────────────────────

@requires_engine
@pytest.mark.parametrize("base_rt,rt_change", _PARAMS)
@pytest.mark.parametrize("seed", [0, 1, 7, 42, 123])
def test_parity_random_sequences(base_rt, rt_change, seed):
    cues, wins = _random_sequence(seed, n=120)
    windows = _assert_parity(cues, wins, base_rt, rt_change)
    # guard against a vacuous pass: adaptation must actually have moved the window
    assert any(w != pytest.approx(base_rt) for w in windows)


@requires_engine
@pytest.mark.parametrize("base_rt,rt_change", _PARAMS)
@pytest.mark.parametrize("cues,wins", [_ALL_WINS, _ALL_MISS, _BOUNDARY])
def test_parity_edge_cases(base_rt, rt_change, cues, wins):
    _assert_parity(list(cues), list(wins), base_rt, rt_change)


@requires_engine
def test_parity_check_is_discriminating():
    """A deliberately wrong Python result must NOT match the reference — proves
    the comparison can actually fail, so a passing parity run is meaningful."""
    cues, wins = _random_sequence(seed=99, n=40)
    ref = _octave_windows(cues, wins, config.BASE_RT_S, config.RT_CHANGE_S)
    perturbed = list(ref)
    perturbed[-1] += 0.020  # one trial off by a full rt_change step
    assert perturbed != pytest.approx(ref, abs=1e-12)
