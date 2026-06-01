# mid-task-deterministic

A PsychoPy implementation of the Monetary Incentive Delay (MID) task for fMRI, adapted from [`mid-task`](../mid-task). Participants respond to a briefly displayed target to earn or avoid losing money.

Unlike `mid-task`, this variant is **deterministic**:

- No adaptive QUEST staircase — target duration is fixed per difficulty level.
- Six cues from a 2 × 3 design (valence × magnitude), following the `fmo-task` scheme:
  - Circle (gain) with low/mid/high line → `+$0`, `+$1`, `+$5`
  - Square (loss) with low/mid/high line → `-$0`, `-$1`, `-$5`
- Three fixed difficulty levels (`low`, `medium`, `high`) control target display duration.

## Documentation

| Document | Description |
|----------|-------------|
| [Usage Guide](docs/usage.md) | Running the task, startup dialog, keyboard controls, and output files |
| [Development Guide](docs/development.md) | Developer setup, project structure, and key constants |

## Quick Start

UV is used for development; Anaconda is the production environment. Both install from the same
`pyproject.toml` — see the [Development Guide](docs/development.md) for details.

**UV (development):**

```bash
uv venv && uv sync
mid-task-det
```

**Anaconda (production):**

```bash
conda env create -f environment.yml
conda activate mid-task-deterministic
mid-task-det
```
