from threading import Lock

from app.id_generator.clock import Clock, SystemClock
from app.id_generator.exceptions import (
    ClockRollbackError,
    InvalidWorkerIdError,
)


class SnowflakeGenerator:
    TIMESTAMP_BITS = 41
    WORKER_ID_BITS = 10
    SEQUENCE_BITS = 12

    MAX_WORKER_ID = (1 << WORKER_ID_BITS) - 1
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1

    WORKER_ID_SHIFT = SEQUENCE_BITS
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS

    def __init__(
        self,
        worker_id: int,
        epoch_ms: int,
        clock: Clock | None = None,
        max_clock_rollback_ms: int = 5,
    ):
        if not 0 <= worker_id <= self.MAX_WORKER_ID:
            raise InvalidWorkerIdError(
                f"worker_id must be between 0 and "
                f"{self.MAX_WORKER_ID}"
            )

        self.worker_id = worker_id
        self.epoch_ms = epoch_ms
        self.clock = clock or SystemClock()
        self.max_clock_rollback_ms = max_clock_rollback_ms

        self.sequence = 0
        self.last_timestamp = -1

        self._lock = Lock()

    def generate(self) -> int:
        with self._lock:
            current_timestamp = self.clock.now_ms()

            timestamp = current_timestamp - self.epoch_ms

            if timestamp < 0:
                raise ClockRollbackError(
                    "Current time is before the configured "
                    "Snowflake epoch"
                )

            if current_timestamp < self.last_timestamp:
                rollback_ms = (
                    self.last_timestamp - current_timestamp
                )

                if rollback_ms > self.max_clock_rollback_ms:
                    raise ClockRollbackError(
                        f"Clock moved backward by {rollback_ms}ms"
                    )

                current_timestamp = self._wait_until(
                    self.last_timestamp
                )

                timestamp = current_timestamp - self.epoch_ms

            if current_timestamp == self.last_timestamp:
                self.sequence += 1

                if self.sequence > self.MAX_SEQUENCE:
                    current_timestamp = self._wait_until(
                        self.last_timestamp + 1
                    )

                    timestamp = current_timestamp - self.epoch_ms
                    self.sequence = 0

            else:
                self.sequence = 0

            self.last_timestamp = current_timestamp

            return (
                (timestamp << self.TIMESTAMP_SHIFT)
                | (self.worker_id << self.WORKER_ID_SHIFT)
                | self.sequence
            )

    def _wait_until(self, target_timestamp: int) -> int:
        current_timestamp = self.clock.now_ms()

        while current_timestamp < target_timestamp:
            remaining_ms = target_timestamp - current_timestamp

            self.clock.sleep_ms(
                min(remaining_ms, 1)
            )

            current_timestamp = self.clock.now_ms()

        return current_timestamp