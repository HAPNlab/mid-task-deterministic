"""
Deterministic boundary tests for trial.run_response hit/miss classification.

The concern these tests pin down: a keypress that physically lands while the
target is still on screen — including the *very last* visible frame — must be
scored as a hit, and must stay a hit even if getKeys() doesn't read it until
several flips after the target was removed. Conversely, the first frame after
removal must score as a miss.

To make this exact and repeatable (no real wall clock, no real display), the
whole phase runs on a shared virtual clock that advances by exactly one frame
per win.flip(). Both the phase clock and the keyboard clock read that virtual
time, and win.lastFrameT is stamped from it — so onset/removal flips land on
known instants and we can place presses relative to the frame grid by hand.

With frame_dur = 0.01 s, jitter = 0.025 s, target_dur = 0.05 s (=> 5 frames):
  - target-onset flip at virtual t = 0.04  (kb.clock reset to 0 here)
  - target visible across frames [0.04, 0.09) wall  ==  [0.00, 0.05) kb-time
  - removal flip at virtual t = 0.09  => target_removed_at = 0.05
So a press is a HIT iff its hardware rt is in [0, 0.05); the last visible frame
is kb-time [0.04, 0.05) and the first frame after removal is [0.05, 0.06).
"""
from __future__ import annotations

import pytest

from mid_det import config, trial

FRAME_DUR = 0.01
JITTER_S = 0.025
TARGET_DUR_S = 0.05  # round(0.05 / 0.01) = 5 frames
EXPECTED_REMOVED_AT = 0.05  # n_target_frames * frame_dur


class _Virtual:
    """Shared virtual wall clock; only win.flip() advances it."""

    def __init__(self) -> None:
        self.t = 0.0


class _FakeClock:
    """Stand-in for core.Clock / kb.clock reading the shared virtual time."""

    def __init__(self, virtual: _Virtual) -> None:
        self._v = virtual
        self._zero = virtual.t

    def reset(self) -> None:
        self._zero = self._v.t

    def getTime(self) -> float:
        return self._v.t - self._zero


class _FakeWindow:
    """Advances virtual time one frame per flip; runs callOnFlip callbacks."""

    def __init__(self, virtual: _Virtual, frame_dur: float) -> None:
        self._v = virtual
        self._frame_dur = frame_dur
        self.lastFrameT = virtual.t
        self.nDroppedFrames = 0
        self._cbs: list = []

    def callOnFlip(self, fn, *args, **kwargs) -> None:
        self._cbs.append((fn, args, kwargs))

    def flip(self) -> None:
        # Advance, then stamp lastFrameT, then fire callbacks. This mirrors
        # PsychoPy: lastFrameT is set right after the swap, before callOnFlip
        # callbacks run (see trial.run_response comments).
        self._v.t += self._frame_dur
        self.lastFrameT = self._v.t
        cbs, self._cbs = self._cbs, []
        for fn, args, kwargs in cbs:
            fn(*args, **kwargs)


class _FakeKeyPress:
    def __init__(self, name: str, rt: float) -> None:
        self.name = name
        self.rt = rt


class _FakeKeyboard:
    """
    getKeys() returns each scripted press once virtual time reaches its
    `arrive` time and the key is in the requested keyList. `rt` is the
    hardware timestamp reported regardless of when the press is read — this
    is what lets us separate "when it was pressed" from "when it was read".
    """

    def __init__(self, virtual: _Virtual) -> None:
        self._v = virtual
        self.clock = _FakeClock(virtual)
        self._scripted: list[dict] = []

    def add_press(self, name: str, rt: float, arrive: float) -> None:
        self._scripted.append({"name": name, "rt": rt, "arrive": arrive, "done": False})

    def getKeys(self, keyList=None, waitRelease=True):
        out = []
        for p in self._scripted:
            if p["done"]:
                continue
            if keyList is not None and p["name"] not in keyList:
                continue
            if self._v.t + 1e-12 >= p["arrive"]:
                p["done"] = True
                out.append(_FakeKeyPress(p["name"], p["rt"]))
        return out

    def clearEvents(self, *args, **kwargs) -> None:
        pass


def _drive(presses, *, early_press=False, monkeypatch):
    """Run run_response on the virtual clock with the given scripted presses."""
    virtual = _Virtual()
    win = _FakeWindow(virtual, FRAME_DUR)
    kb = _FakeKeyboard(virtual)
    for name, rt, arrive in presses:
        kb.add_press(name, rt, arrive)

    # Target draws need a real window; patch them out — geometry is irrelevant
    # to the timing classification under test.
    monkeypatch.setattr(trial, "draw_target", lambda *a, **k: None)
    monkeypatch.setattr(trial, "draw_fixation_x", lambda *a, **k: None)
    # phase_clock = core.Clock() inside run_response -> bind to virtual time.
    monkeypatch.setattr(trial.core, "Clock", lambda *a, **k: _FakeClock(virtual))

    return trial.run_response(
        win,
        object(),  # stimuli: unused once draws are patched out
        kb,
        JITTER_S,
        TARGET_DUR_S,
        FRAME_DUR,
        early_press,
    )


def test_press_on_last_visible_frame_is_hit(monkeypatch):
    # rt = 0.045 falls in the last visible frame's kb-window [0.04, 0.05).
    # Physical read time (arrive) is the natural ~0.085 (= 0.04 + rt).
    hit, rt_s, early, removed_at, diag = _drive(
        [("1", 0.045, 0.085)], monkeypatch=monkeypatch
    )
    assert removed_at == pytest.approx(EXPECTED_REMOVED_AT, abs=1e-9)
    assert hit is True
    assert early is False
    assert rt_s == pytest.approx(0.045)


def test_press_first_frame_after_removal_is_miss(monkeypatch):
    # rt = 0.055 is one frame past removal (kb-window [0.05, 0.06)) -> miss,
    # but the RT is still recorded.
    hit, rt_s, early, removed_at, diag = _drive(
        [("1", 0.055, 0.095)], monkeypatch=monkeypatch
    )
    assert removed_at == pytest.approx(EXPECTED_REMOVED_AT, abs=1e-9)
    assert hit is False
    assert early is False
    assert rt_s == pytest.approx(0.055)


def test_last_frame_press_read_late_is_still_hit(monkeypatch):
    # The crucial decoupling: physically pressed on the last visible frame
    # (rt = 0.045) but not READ by getKeys until t = 0.15 — long after the
    # target was removed at t = 0.09. Classification uses the hardware rt, not
    # the read time, so this must remain a hit (no false miss).
    hit, rt_s, early, removed_at, diag = _drive(
        [("1", 0.045, 0.15)], monkeypatch=monkeypatch
    )
    assert hit is True
    assert early is False
    assert rt_s == pytest.approx(0.045)


def test_negative_rt_is_early_not_hit(monkeypatch):
    # A press with rt < 0 (pressed before the onset-flip clock reset) is an
    # early press, never a hit.
    hit, rt_s, early, removed_at, diag = _drive(
        [("1", -0.005, 0.085)], monkeypatch=monkeypatch
    )
    assert early is True
    assert hit is False


def test_no_press_is_miss(monkeypatch):
    hit, rt_s, early, removed_at, diag = _drive([], monkeypatch=monkeypatch)
    assert hit is False
    assert rt_s is None
    assert early is False
    assert removed_at == pytest.approx(EXPECTED_REMOVED_AT, abs=1e-9)


def test_just_below_and_just_above_removal_boundary(monkeypatch):
    # Tighten the boundary to sub-frame: 1 ms below removal -> hit,
    # 1 ms above -> miss. Confirms the half-open [0, target_removed_at) window.
    hit_below, _, _, _, _ = _drive([("1", 0.049, 0.089)], monkeypatch=monkeypatch)
    hit_above, _, _, _, _ = _drive([("1", 0.051, 0.099)], monkeypatch=monkeypatch)
    assert hit_below is True
    assert hit_above is False
