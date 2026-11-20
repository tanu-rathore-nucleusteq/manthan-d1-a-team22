"""Applies the configured latency, error rate or outage to each request."""

import random
import threading
import time

from mock_gateway.dtos import FaultSettings


class FaultSwitches:
    """The live fault settings, shared by every request and replaced by POST /admin/faults."""

    def __init__(self, settings: FaultSettings) -> None:
        self._settings = settings
        self._lock = threading.Lock()

    @property
    def current(self) -> FaultSettings:
        with self._lock:
            return self._settings

    def update(self, settings: FaultSettings) -> None:
        with self._lock:
            self._settings = settings

    def outage(self) -> bool:
        return self.current.down

    def transient_error(self) -> bool:
        # Simulation only, not security: an ordinary random number is right here.
        return random.random() < self.current.error_rate  # noqa: S311

    def delay(self) -> None:
        latency_ms = self.current.latency_ms
        if latency_ms:
            time.sleep(latency_ms / 1000)
