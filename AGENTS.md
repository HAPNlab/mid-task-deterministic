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

`psyexp-core` is a **published PyPI package**, declared in `[project].dependencies` as
`psyexp-core>=X.Y`; the exact version is pinned in `uv.lock` so both uv and pip/conda resolve the
same core, and every run's `manifest.json` records the resolved `psyexp_core_version`.

To **co-develop** the core against this task, overlay an editable sibling checkout. The catch:
`uv.lock` is authoritative, so *any* `uv sync` reverts the overlay back to the locked PyPI version —
`--inexact` does **not** help (it only spares packages absent from the lock, and the core is in it).
The one thing that preserves the overlay is skipping the sync:

```sh
uv pip install -e ../psyexp-core
uv run --no-sync pytest        # or: export UV_NO_SYNC=1 for the shell
```

The `just` recipes wrap this: `just core-dev` overlays the editable checkout, then `just core-run` /
`just core-test` run with `--no-sync`; `just core-release` drops it (plain `uv sync`). Don't run a
bare `uv sync`/`uv run` while overlaying — it silently reverts the editable core. For a setup that
survives sync, declare the path source in `pyproject.toml`
(`[tool.uv.sources] psyexp-core = { path = "../psyexp-core", editable = true }`) and keep that edit
local with `git update-index --skip-worktree pyproject.toml uv.lock` so it never lands in a commit.

**Updating to a new `psyexp-core` release:** a bare `uv sync` won't move it — it installs exactly
what `uv.lock` pins. Re-resolve the lock, then apply it (or run `just core-upgrade`):

```sh
uv lock --upgrade-package psyexp-core   # rewrite uv.lock to the newest version the constraint allows
uv sync
```

Commit the updated `uv.lock` (and bump the `>=` floor in `pyproject.toml` first if you want to
require a new minimum).