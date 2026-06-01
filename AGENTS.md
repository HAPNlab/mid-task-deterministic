This project uses UV for managing Python packages.

It's recommended to use Python through UV, but if you need to, `python3` is available while `python` is not.

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