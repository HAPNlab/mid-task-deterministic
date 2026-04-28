# Usage Guide

This guide covers how to run the deterministic MID task.

## Overview

A PsychoPy-based fMRI task adapted from `mid-task`. On each trial, participants see a cue indicating potential gain ($0/$1/$5) or loss ($0/$1/$5), then must press a button while a brief target is on screen to earn or avoid losing that amount. **Target duration is fixed per difficulty level** — there is no adaptive staircase.

## Launching the Task

```bash
mid-task-det
```

Or without installation:

```bash
uv run mid-task-det
```

## Startup Dialog

| Field | Description | Example |
|-------|-------------|---------|
| **Subject ID** | Participant identifier; used in output filenames | `ABC123` |
| **fMRI? (yes/no)** | Enable hardware TR pulse sync and fMRI keyboard layout | `yes` |
| **Task number (1/2/practice)** | Which sequence to run | `1` |
| **Show instructions? (yes/no)** | Display instruction slides before the task begins | `yes` |

## Modes

### fMRI Mode (`fmri = yes`)

- Waits for the first hardware TR pulse from the MCC DAQ counter board before starting
- Uses the scanner keyboard layout (numpad keys)

### Behavioral Mode (`fmri = no`)

- Press **0** to start the task when the "waiting" screen appears
- Uses the standard keyboard layout
- TR timing is emulated in software

## Keyboard Controls

### Behavioral Mode

| Key | Action |
|-----|--------|
| `4` | Navigate instructions forward |
| `3` | Navigate instructions backward |
| `0` | Start task / advance past instructions finish screen |
| `1`–`10` | Response button during target |
| `Escape` or `l` | Quit at any time |

### fMRI Mode

| Key | Action |
|-----|--------|
| `7` | Navigate instructions forward |
| `6` | Navigate instructions backward |
| `0` | Advance past instructions finish screen |
| `1`–`10` | Response button during target |
| `Escape` or `l` | Quit at any time |

## Trial Structure

```
Cue (2 s) → Fixation (2 s) → Response (2 s) → Outcome (2 s) → ITI (2–4 s)
```

### Cue Types

Six cues from a 2 × 3 design (valence × magnitude):

| Cue | Shape | Line position | Hit outcome | Miss outcome |
|-----|-------|---------------|-------------|--------------|
| `+$0` | Circle | bottom | +$0 | $0 |
| `+$1` | Circle | middle | +$1 | $0 |
| `+$5` | Circle | top | +$5 | $0 |
| `-$0` | Square | bottom | $0 | -$0 |
| `-$1` | Square | middle | $0 | -$1 |
| `-$5` | Square | top | $0 | -$5 |

During the response phase, target onset is delayed by a random pre-target jitter
uniformly sampled from **250–1000 ms**.

### Fixed Target Duration per Difficulty

| Difficulty | Target duration |
|------------|-----------------|
| `low` | 150 ms (hard) |
| `medium` | 265 ms |
| `high` | 400 ms (easy) |

Values are defined in `src/mid_det/config.py` (`TARGET_DUR_S`).

## Run Structure

1. **Initial fixation** – 12 s crosshair before the first trial
2. **Trial loop** – 54 trials (practice: 18 trials)
3. **Closing fixation** – 8 s crosshair after the last trial
4. **End screen** – Press `0` to exit

`early_press` is set when a response key is pressed any time from fixation onset
through target onset (fixation-window checking is intentional).

ITI duration is sequence-driven as `n_iti` TR units (each unit = 2 s), yielding
2 s or 4 s ITIs in the shipped sequences.

## Output Files

Each run creates a timestamped directory under `data/`:

```
data/
└── ABC123_run1_20260421T143000/
    ├── manifest.json
    ├── behavioral_ABC123_run1.csv
    ├── scan_log_ABC123_run1.csv
    └── experiment.log
```

### behavioral CSV columns

| Column | Description |
|--------|-------------|
| `trial_n` | Trial number (1-indexed) |
| `trial_type` | Integer 1–18 encoding valence×magnitude×difficulty |
| `valence` | `gain` or `loss` |
| `magnitude` | 0, 1, or 5 |
| `difficulty` | `low`, `medium`, or `high` |
| `cue_label` | On-screen label (e.g. `+$5`, `-$1`) |
| `target_dur_ms` | Target display duration (ms) — fixed per difficulty |
| `jitter_ms` | Random onset jitter within response phase (ms) |
| `early_press` | 1 if a button was pressed during fixation |
| `hit` | 1 if target was pressed while visible |
| `rt_ms` | Reaction time from target onset (ms); blank if no response |
| `reward_outcome` | Outcome label (e.g. `+$5`, `$0`, `-$1`) |
| `total_earned` | Cumulative earnings after this trial ($) |
| `time_onset` | Trial onset time relative to scan start (s) |
| `timing_drift_ms` | Deviation from scheduled trial end time (ms) |
| `pulse_ct` | Scanner pulse count at trial onset |

### scan_log CSV

One row per trial phase: `trial_n`, `phase`, `tr_n`, `phase_global_time`, `phase_trial_time`, `pulse_ct`.

## Quitting Early

Press **Escape** or **l** at any point to quit. Output files written up to that point are saved.
