# Contributing to mid-task-deterministic

Thanks for your interest in contributing! This is a PsychoPy implementation of a
deterministic Monetary Incentive Delay (MID) task for fMRI. Because it is used to
run real experiments, correctness, timing fidelity, and reproducibility matter
more than feature velocity. The guidelines below keep contributions safe to deploy
on lab and scanner machines.

## Ways to contribute

- **Report a bug** — crashes, incorrect stimuli/timing, or output-file problems.
- **Request a feature** — new functionality or tooling.
- **Improve documentation** — the [usage](docs/usage.md) and
  [development](docs/development.md) guides.

Please open an [issue](https://github.com/HAPNlab/mid-task-deterministic/issues/new/choose)
using the appropriate template before starting significant work, so we can agree on
the approach first.

## Development setup

UV is the canonical development workflow (it owns the pinned `uv.lock`); Anaconda
is the production environment. Both install from the same `pyproject.toml`. See the
[Development Guide](docs/development.md) and [AGENTS.md](AGENTS.md) for full details.

```bash
# Development (UV)
uv venv && uv sync
uv run pytest

# Production parity check (Anaconda)
conda env create -f environment.yml
conda activate mid-task-deterministic
```

The MATLAB-parity test (`tests/test_calibration_matlab_parity.py`) needs GNU Octave
or MATLAB on `PATH` to run the reference algorithm. Install Octave with
`brew install octave`. Without an engine the test **skips with a loud warning**
rather than silently passing.

## Commit messages and versioning

- This project follows [Semantic Versioning](https://semver.org/). For research code,
  treat any change that affects **data comparability** (stimuli, timing, response
  criterion, output schema) as at least a MINOR bump — usually MAJOR. See the
  [Release Guide](docs/releasing.md) for how versions are decided, verified, and cut.
- Write commit messages in the
  [Conventional Commits](https://www.conventionalcommits.org/) style:
  `type(scope): summary` (e.g. `fix(trial): correct target frame count`). Common types:
  `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`. Mark breaking changes with
  a `!` (`feat!: ...`) or a `BREAKING CHANGE:` footer. This keeps the changelog and
  version bumps predictable.

## Making changes

1. **Fork and branch.** Create a topic branch off `main` (e.g. `fix/target-timing`).
2. **Keep imports headless-safe.** Source modules guard their `psychopy` imports in
   `try/except` so the logic and timing tests import and run without a display or
   audio device. CI does **not** install PsychoPy — do not add a hard top-level
   `import psychopy` to any module exercised by the test suite.
3. **Add or update tests** for the behavior you change. Logic and timing should be
   covered by headless tests.
4. **Update the docs and CHANGELOG.** Add a `CHANGELOG.md` entry (the format follows
   [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)) and update the usage or
   development guides if behavior changes.
5. **Preserve UV/conda parity.** If you touch dependencies, update both
   `pyproject.toml` and `environment.yml`, and refresh `uv.lock` (`uv sync`).

See the [Release Guide](docs/releasing.md) for how changes become tagged releases and
what verification (timing via screen recordings, task measurements) gates a stable
versus a pre-release (`-alpha`/`-beta`/`-rc`) version.

## Before opening a pull request

Run the full check that CI runs:

```bash
uv run pytest -v --ignore=tests/test_overlay.py
```

(`tests/test_overlay.py` is a manual `visual.Window` script that needs a live
display; it is intentionally excluded from automated runs.)

Confirm each item:

- [ ] Tests pass (`uv run pytest`), including the Octave/MATLAB parity test where an engine is available.
- [ ] Changes are headless/CI safe — logic & timing tests run without PsychoPy or a display.
- [ ] Documentation and `CHANGELOG.md` are updated.
- [ ] Changes work under both the UV (`uv.lock`) and conda (`environment.yml`) workflows.

## Pull request process

- Fill out the [pull request template](.github/PULL_REQUEST_TEMPLATE.md) completely.
- Link the issue your PR addresses (e.g. `Closes #123`).
- Keep PRs focused; smaller, single-purpose PRs are reviewed faster.
- A maintainer will review and may request changes. CI (the `tests` workflow) must
  be green before merge.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE.md).
