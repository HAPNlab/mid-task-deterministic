"""Rich console live-view for the trial table."""
from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.table import Table
import rich.box


_DIM = "[dim]…[/dim]"


@dataclass
class _RowData:
    trial_label: str
    cue_label: str
    window_str: str = _DIM
    result_cell: str = _DIM
    rt_str: str = _DIM
    outcome_str: str = _DIM
    total_str: str = _DIM
    hit_rate_str: str = _DIM


def _make_table(rows: list[_RowData]) -> Table:
    t = Table(box=rich.box.SIMPLE_HEAD)
    t.add_column("#", justify="right")
    t.add_column("Cue")
    t.add_column("Window", justify="right")
    t.add_column("Result")
    t.add_column("RT", justify="right")
    t.add_column("Outcome", justify="right")
    t.add_column("Total", justify="right")
    t.add_column("Hit %", justify="right")
    for r in rows:
        t.add_row(
            r.trial_label, r.cue_label, r.window_str,
            r.result_cell, r.rt_str, r.outcome_str, r.total_str, r.hit_rate_str,
        )
    return t


class TrialLiveView:
    """Manages the Rich Live table showing per-trial progress."""

    def __init__(self, console: Console, n_trials: int) -> None:
        self._n_trials = n_trials
        self._live = Live(console=console, auto_refresh=False)
        self._rows: list[_RowData] = []
        self._current: _RowData | None = None
        self._n_hits_snapshot = 0
        self._n_done_snapshot = 0

    def __enter__(self) -> TrialLiveView:
        self._live.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._live.__exit__(*args)

    def start_trial(self, trial_n: int, cue_label: str, n_hits: int, n_done: int) -> None:
        """Add a partial row at the start of a trial."""
        self._n_hits_snapshot = n_hits
        self._n_done_snapshot = n_done
        self._current = _RowData(
            trial_label=f"{trial_n}/{self._n_trials}",
            cue_label=cue_label,
        )
        self._rows.append(self._current)
        self._refresh()

    def on_response(
        self, hit: bool, rt_s: float | None, early_press: bool, target_dur_ms: int
    ) -> None:
        """Called by run_trial after the response phase."""
        r = self._current
        assert r is not None
        r.window_str = f"{target_dur_ms} ms"
        if hit:
            r.result_cell = "[green]HIT[/green]"
        elif early_press:
            r.result_cell = "[yellow]early[/yellow]"
        else:
            r.result_cell = "[red]miss[/red]"
        r.rt_str = f"{rt_s * 1000:.0f} ms" if rt_s is not None else "—"
        self._refresh()

    def on_outcome(self, reward_outcome: str, new_total_earned: int, hit: bool) -> None:
        """Called by run_trial right after the outcome phase."""
        r = self._current
        assert r is not None
        r.outcome_str = reward_outcome
        r.total_str = f"${new_total_earned}"
        hit_rate = (self._n_hits_snapshot + int(hit)) / (self._n_done_snapshot + 1) * 100
        r.hit_rate_str = f"{hit_rate:.0f}%"
        self._refresh()

    def _refresh(self) -> None:
        self._live.update(_make_table(self._rows))
        self._live.refresh()
