from datetime import UTC, datetime
from time import sleep
from typing import Protocol


class Clock(Protocol):
    def now_ms(self) -> int:
        ...

    def sleep_ms(self, milliseconds: int) -> None:
        ...


class SystemClock:
    def now_ms(self) -> int:
        return int(
            datetime.now(UTC).timestamp() * 1000
        )

    def sleep_ms(self, milliseconds: int) -> None:
        sleep(milliseconds / 1000)
