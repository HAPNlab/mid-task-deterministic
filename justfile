# mid-task-deterministic dev tasks. Run `just` to list recipes.
# Requires `just` (https://github.com/casey/just): `brew install just`.

# Show available recipes
default:
    @just --list

# Install/refresh the venv from the locked PyPI psyexp-core
sync:
    uv sync

# Run the experiment (locked PyPI core)
run *args:
    uv run mid-task-det {{args}}

# Run the standalone cue-ratings survey
ratings *args:
    uv run mid-ratings-det {{args}}

# Run the test suite
test *args:
    uv run pytest {{args}}

# --- Co-developing psyexp-core from ../psyexp-core ---------------------------
# uv.lock is authoritative, so a plain `uv sync`/`uv run` reverts an editable
# overlay back to the locked PyPI version. `--inexact` does NOT prevent this — it
# only spares packages absent from the lock, and the core is in it. The only way
# to keep the overlay is to skip the sync, which these recipes do via --no-sync.

# Overlay an editable sibling checkout of ../psyexp-core
core-dev:
    uv pip install -e ../psyexp-core
    @echo "Editable psyexp-core overlaid. Use 'just core-run' / 'just core-test' so it isn't reverted."

# Run the experiment against the editable overlay (skips the revert-causing sync)
core-run *args:
    uv run --no-sync mid-task-det {{args}}

# Run the tests against the editable overlay
core-test *args:
    uv run --no-sync pytest {{args}}

# Drop the overlay and restore the locked PyPI psyexp-core
core-release:
    uv sync

# Upgrade to the newest published psyexp-core and update the lock
core-upgrade:
    uv lock --upgrade-package psyexp-core
    uv sync
