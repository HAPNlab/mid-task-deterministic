"""
Scanner backend abstraction and PulseCounter.

ScannerBackend – protocol implemented by:
  HardwareBackend  – real MCC DAQ counter board
  EmulatedBackend  – software TR clock for development without scanner hardware

PulseCounter – wait/drain logic built on top of a backend; agnostic to which.
"""
from __future__ import annotations

from typing import Protocol

from mid_det import config


class ScannerBackend(Protocol):
    pulse_rate: int

    def read(self) -> int: ...

    def start(self) -> None: ...


class HardwareBackend:
    """MCC DAQ counter board backend."""

    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        try:
            from mcculw import ul
            from mcculw.device_info import DaqDeviceInfo
        except Exception as exc:
            raise RuntimeError(
                "mcculw unavailable (Windows-only DAQ library). "
                "Run without fmri=True or use EmulatedBackend for testing."
            ) from exc
        self._board_num = config.BOARD_NUM
        ctr_info = DaqDeviceInfo(self._board_num).get_ctr_info()
        self._counter_num = ctr_info.chan_info[0].channel_num
        self._ul = ul

    def read(self) -> int:
        return self._ul.c_in_32(self._board_num, self._counter_num)

    def start(self) -> None:
        pass


class EmulatedBackend:
    """Software TR clock for development without scanner hardware."""

    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        self._emu_start: float | None = None

    def start(self) -> None:
        from time import perf_counter
        self._emu_start = perf_counter()

    def read(self) -> int:
        if self._emu_start is None:
            return 0
        from time import perf_counter
        elapsed = perf_counter() - self._emu_start
        tr_s = config.MR_SETTINGS["TR"]
        return int(elapsed / tr_s * self.pulse_rate)


def make_backend(fmri: bool) -> ScannerBackend:
    if fmri:
        return HardwareBackend()
    return EmulatedBackend()


class PulseCounter:
    def __init__(self, backend: ScannerBackend) -> None:
        self._backend = backend
        self._last = backend.read()

    def wait_for_start(self) -> None:
        from time import sleep
        while self._backend.read() == self._last:
            sleep(0.001)
        self._last = self._backend.read()

    def drain(self) -> int:
        curr = self._backend.read()
        delta = max(0, curr - self._last)
        self._last = curr
        return delta

    def wait_for_tr(self) -> int:
        from time import sleep
        target = self._last + self._backend.pulse_rate
        while self._backend.read() < target:
            sleep(0.001)
        curr = self._backend.read()
        delta = curr - self._last
        self._last = curr
        return delta
