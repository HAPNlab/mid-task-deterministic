This project uses UV for managing Python packages.

It's recommended to use Python through UV, but if you need to, `python3` is available while `python` is not.

The calibration MATLAB-parity test (`tests/test_calibration_matlab_parity.py`) needs GNU Octave (or
MATLAB) on PATH to run the reference algorithm; install it with `brew install octave`. Without an
engine the test skips with a loud warning rather than silently passing.

## Environments: UV (development) vs. Anaconda (production)

- **UV is for development.** It is the canonical local workflow and the only one with a pinned
  lockfile (`uv.lock`). Use it for iteration and tests (`uv sync`, `uv run pytest`).
- **Anaconda is for production.** The task is deployed/run inside conda environments (e.g. lab/
  scanner machines) via `environment.yml`.

`pyproject.toml` is the shared, standard manifest both tools read — its `[build-system]` and
`[project]` tables are PEP 517/621 standards. Conda does not read `pyproject.toml` directly:
`environment.yml` provisions Python (plus heavy binary libs), then **pip** installs this package
and its PyPI dependencies from `pyproject.toml` (`pip install -e .`). The UV-only sections
(`[tool.uv.*]`) and `uv.lock` are silently ignored by pip/conda, so no `pyproject.toml` changes are
needed to support conda — conda just resolves dependencies fresh from PyPI instead of from the
lockfile.

## Shared harness: psyexp-core

The generic experiment plumbing — fullscreen window + VSYNC/frame-timing setup, timestamped run
directories, the `CsvWriter` base, run-manifest writing, setup-wizard primitives, the instruction
pager, and the keyboard abstraction — lives in the shared [`psyexp-core`](https://github.com/HAPNlab/psyexp-core)
package. This repo keeps only MID-specific logic (trial loop, reward rule, adaptive staircase,
sequences, ratings survey, legacy MATLAB CSV) and consumes the harness as a dependency.

`psyexp-core` is pinned by **git tag** in `[project].dependencies` as a PEP 508 direct reference
(`psyexp-core @ git+https://github.com/HAPNlab/psyexp-core.git@vX.Y.Z`), so both uv and pip/conda
resolve the same core, and every run's `manifest.json` records the resolved `psyexp_core_version`.

To **co-develop** the core against this task, overlay an editable sibling checkout and skip the
re-sync that would revert it to the pinned tag:

```sh
uv pip install -e ../psyexp-core
uv run --no-sync pytest        # or: export UV_NO_SYNC=1
```

Bump the pinned tag in `pyproject.toml` (and re-run `uv lock`) once a new `psyexp-core` release is
tagged.