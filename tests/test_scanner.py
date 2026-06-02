"""Tests for PulseCounter."""
from __future__ import annotations

from mid_det import config
from mid_det.scanner import PulseCounter


class FakeBackend:
    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        self._count = 0

    def read(self) -> int:
        return self._count

    def start(self) -> None:
        pass

    def advance(self, n: int) -> None:
        self._count += n


def test_pulse_counter_drain():
    be = FakeBackend()
    pc = PulseCounter(be)
    assert pc.drain() == 0
    be.advance(3)
    assert pc.drain() == 3
    assert pc.drain() == 0
