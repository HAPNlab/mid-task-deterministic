# Development Guide

This guide covers setting up and developing `mid-task-deterministic`.

## Prerequisites

- Python 3.11+
- One of:
  - [UV](https://docs.astral.sh/uv/) – Fast Python package installer and resolver (**development**)
  - [Anaconda / Miniconda](https://docs.conda.io/) (**production** deployment environment)
- macOS or Windows (PsychoPy supports both; MCC DAQ hardware is Windows-only)

### macOS

```bash
brew install hdf5 openblas lapack
```

### Windows (fMRI hardware mode)

The MCC DAQ counter board (used to read scanner TR pulses) requires:

- [Instacal](https://www.mccdaq.com/Software-Downloads)
- `mcculw` Python package (installed via `uv sync`)

Configure your DAQ board number in `src/mid_det/config.py` (`BOARD_NUM`).

## Quick Start

UV is the development workflow; Anaconda is the production run environment. Both install the
package from the same `pyproject.toml`.

### UV (development)

```bash
uv venv
uv sync --all-extras
uv run mid-task-det
```

### Anaconda / conda (production)

Conda provisions Python (and heavy binary libs), then pip installs the package from
`pyproject.toml`:

```bash
conda env create -f environment.yml
conda activate mid-task-deterministic
mid-task-det
```

Or into an existing/custom environment:

```bash
conda create -n mid python=3.11
conda activate mid
pip install -e ".[dev]"
```

`pyproject.toml` is the shared, standard manifest. The UV-specific pieces (`[tool.uv.*]`,
`uv.lock`) are ignored by pip/conda, so the conda install resolves dependencies fresh from PyPI
rather than from the lockfile.

## Project Structure

```
mid-task-deterministic/
├── src/
│   └── mid_det/
│       ├── __init__.py       # Version
│       ├── __main__.py       # Entry point; wires all modules together
│       ├── config.py         # All task constants (no cross-module imports)
│       ├── display.py        # PsychoPy stimuli construction and draw helpers
│       ├── recorder.py       # TrialRecord, ScanPhase, CSV writers, manifest
│       ├── scanner.py        # HardwareBackend, EmulatedBackend, PulseCounter
│       ├── session.py        # Startup dialog, screen setup, sequence loading
│       └── trial.py          # Per-phase functions and run_trial()
├── sequences/
│   ├── run_1.csv             # 54-trial sequence for run 1
│   ├── run_2.csv             # 54-trial sequence for run 2
│   └── practice.csv          # 18-trial practice (one trial per condition)
├── text/
│   └── instructions_MID.txt  # Instruction pages (one line per page)
├── data/                     # Output directory (created at runtime)
├── tests/
├── docs/
└── pyproject.toml
```

## Module Overview

| Module | Responsibility |
|--------|---------------|
| `config.py` | Single source of truth for all timing, keyboard, scanner, and target-duration constants |
| `session.py` | Startup GUI dialog, screen/monitor setup, sequence CSV loading, instruction display |
| `display.py` | Build all PsychoPy `Visual` objects; draw helpers for each phase (circle/square cue with magnitude line) |
| `scanner.py` | Abstract scanner backend; `HardwareBackend` (MCC DAQ) and `EmulatedBackend` (software clock) |
| `trial.py` | `run_trial()` and per-phase functions (`run_cue`, `run_fixation`, `run_response`, `run_outcome`, `run_iti`) |
| `recorder.py` | `TrialRecord` and `ScanPhase` dataclasses; CSV writers; `write_manifest()` |
| `__main__.py` | Orchestration: init → instructions → wait for scan → trial loop → cleanup |

## Relationship to `mid-task`

This project is forked from [`mid-task`](../mid-task) at the `next` branch. Key differences:

- **No `quest.py`** — adaptive staircase removed. Target duration is fixed per difficulty level in `config.TARGET_DUR_S`.
- **6 cue types** instead of 3 — adopted from `fmo-task`: 2 polarities × 3 magnitudes (0 / 1 / 5).
- **Magnitude line rendering** — cue shape is an outline (circle for gain, square for loss) with a horizontal line at low/mid/high position to encode magnitude, plus a dollar label below.
- **No accuracy label** shown to participants.
- **Sequence CSV columns**: `polarity, magnitude, difficulty, n_iti`.

## Key Constants (`config.py`)

| Constant | Value | Description |
|----------|-------|-------------|
| `STUDY_TIMES_S` | `{cue: 2.0, fixation: 2.0, response: 2.0, outcome: 2.0, iti: 2.0}` | Phase durations |
| `TARGET_DUR_S` | `{low: 0.150, medium: 0.265, high: 0.400}` | Fixed target duration per difficulty |
| `INITIAL_FIX_DUR_S` | `12.0` | Initial fixation before first trial |
| `CLOSING_FIX_DUR_S` | `8.0` | Closing fixation after last trial |
| `JITTER_MIN_S` | `0.25` | Min pre-target jitter before target onset |
| `JITTER_MAX_S` | `1.0` | Max pre-target jitter before target onset |
| `SCANNER_PULSE_RATE` | `46` | Hardware pulses per TR from MCC counter |

## Scanner Synchronisation

`PulseCounter` wraps a backend and exposes two methods:

- `wait_for_tr()` – blocks until `SCANNER_PULSE_RATE` more pulses arrive, returns delta
- `drain()` – returns pulses accumulated since last call without blocking

In fMRI mode, `HardwareBackend` reads the MCC DAQ counter register directly.
In behavioral/development mode, `EmulatedBackend` simulates pulses at the correct rate based on wall-clock time.

## Testing

```bash
uv run pytest
```

## Sequence Files

Sequences live in `sequences/` as CSV files with columns:

| Column | Values |
|--------|--------|
| `polarity` | `gain`, `loss` |
| `magnitude` | `0`, `1`, `5` |
| `difficulty` | `low`, `medium`, `high` |
| `n_iti` | Number of ITI TRs (1 or 2) for pseudorandom spacing |

Additional implementation choices kept intentionally:
- Early-press checking starts during fixation and continues until target onset.
- Response keys accept `1`-`10`.
