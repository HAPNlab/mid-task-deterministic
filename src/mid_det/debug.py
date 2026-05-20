"""
F3-toggleable debug overlay (Minecraft-style HUD).
DebugState is a plain mutable dataclass updated by the caller each frame/phase.
DebugOverlay wraps a TextStim and draws it before every win.flip() when enabled.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from psychopy import visual


@dataclass
class DebugState:
    subject_id: str = ""
    run_n: str = ""
    fmri: bool = False
    frame_rate: float | None = None
    frame_dur_ms: float | None = None
    trial_n: int = 0
    n_trials: int = 0
    phase: str = "—"
    valence: str = "—"
    magnitude: int = 0
    target_dur_ms: int = 0
    jitter_ms: int = 0
    n_hits: int = 0
    n_trials_done: int = 0
    total_earned: int = 0
    pulse_ct: int = 0
    last_result: str = "—"
    last_rt_ms: float | str = "—"
    last_timing_drift_ms: float = 0.0
    global_time: float = 0.0
    nominal_time: float = 0.0


class DebugOverlay:
    def __init__(self, win: visual.Window, state: DebugState) -> None:
        self.state = state
        self.enabled = False

        self._stim = visual.TextStim(
            win,
            text="",
            pos=(-0.380, 0.430),
            height=0.0200,
            color="yellow",
            font="Courier",
            alignText="left",
            autoLog=False,
        )

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def draw(self) -> None:
        if not self.enabled:
            return
        self._stim.text = self._format()
        self._stim.draw()

    def _format(self) -> str:
        s = self.state
        fps_str = f"{s.frame_rate:.1f} Hz ({s.frame_dur_ms:.2f} ms)" if s.frame_rate else "N/A"
        fmri_str = "Y" if s.fmri else "N"
        hit_rate = f"{s.n_hits / s.n_trials_done * 100:.0f}%" if s.n_trials_done else "—"
        drift_sign = "+" if s.last_timing_drift_ms >= 0 else ""
        return (
            f"[DEBUG]  sub:{s.subject_id}  run:{s.run_n}  fmri:{fmri_str}  fps:{fps_str}\n"
            f"trial:{s.trial_n}/{s.n_trials}  phase:{s.phase}\n"
            f"cue:{s.valence} ${s.magnitude}  win:{s.target_dur_ms} ms  jitter:{s.jitter_ms} ms\n"
            f"hits:{s.n_hits}/{s.n_trials_done} ({hit_rate})  earned:${s.total_earned}  pulse:{s.pulse_ct}\n"
            f"last:{s.last_result}  RT:{s.last_rt_ms}  drift:{drift_sign}{s.last_timing_drift_ms:.1f} ms\n"
            f"t:{s.global_time:.3f} s  sched:{s.nominal_time:.3f} s"
        )
