"""
Per-cue adaptive target-window staircase.

Mirrors MATLAB mid-task `PresentTarget.m` logic:
  - For each cue type (valence, magnitude), track the history of calibrations
    applied and whether each trial was a win.
  - First trial of a cue: window = base_rt.
  - Trials 2..MIN_TRIALS_FOR_ADAPT: keep previous calibration (no change yet).
  - From trial MIN_TRIALS_FOR_ADAPT+1 onwards: cumulative win-ratio
    > WIN_RATIO_THRESHOLD shrinks the window by RT_CHANGE_S; otherwise grows it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from mid_det import config


@dataclass
class CalibrationState:
    base_rt_s: float
    rt_change_s: float = config.RT_CHANGE_S
    win_ratio_threshold: float = config.WIN_RATIO_THRESHOLD
    min_trials_for_adapt: int = config.MIN_TRIALS_FOR_ADAPT
    _last_cal: dict[tuple[str, int], float | None] = field(default_factory=dict)
    _wins: dict[tuple[str, int], list[int]] = field(default_factory=dict)

    def next_target_dur_s(self, valence: str, magnitude: int) -> float:
        """Compute and stage the target window for this trial of (valence, magnitude)."""
        key = (valence, magnitude)
        last = self._last_cal.get(key)
        prior_wins = self._wins.setdefault(key, [])

        if last is None:
            current = self.base_rt_s
        elif len(prior_wins) >= self.min_trials_for_adapt:
            ratio = sum(prior_wins) / len(prior_wins)
            if ratio > self.win_ratio_threshold:
                current = last - self.rt_change_s
            else:
                current = last + self.rt_change_s
        else:
            current = last

        self._last_cal[key] = current
        return current

    def record_outcome(self, valence: str, magnitude: int, hit: bool) -> None:
        self._wins[(valence, magnitude)].append(1 if hit else 0)
