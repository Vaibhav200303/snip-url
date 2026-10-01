import pytest


class FakeClock:
    def __init__(self, timestamp_ms: int):
        self.timestamp_ms = timestamp_ms
        self.sleep_calls = 0

    def now_ms(self) -> int:
        return self.timestamp_ms

    def sleep_ms(self, milliseconds: int) -> None:
        self.sleep_calls += 1
        self.timestamp_ms += milliseconds


# First test — basic generation
from app.id_generator.snowflake import SnowflakeGenerator

EPOCH = 0


def test_generates_positive_id():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    snowflake_id = generator.generate()

    assert snowflake_id > 0


# Test same-millisecond generation
def test_generates_unique_ids_in_same_millisecond():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    ids = [generator.generate() for _ in range(100)]

    assert len(ids) == len(set(ids))


# Test monotonicity
def test_ids_are_monotonically_increasing():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    ids = [generator.generate() for _ in range(100)]

    assert ids == sorted(ids)


# Test sequence overflow
def test_sequence_overflow_moves_to_next_millisecond():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    generator.generate()

    generator.sequence = generator.MAX_SEQUENCE

    generator.generate()

    assert clock.now_ms() >= 1001
    assert generator.sequence == 0


# Test small clock rollback
def test_small_clock_rollback_waits_for_clock_to_catch_up():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
        max_clock_rollback_ms=5,
    )

    first_id = generator.generate()

    clock.timestamp_ms = 999

    second_id = generator.generate()

    assert clock.now_ms() >= 1000
    assert second_id > first_id
    assert clock.sleep_calls > 0


# Test large rollback
from app.id_generator.exceptions import ClockRollbackError


def test_large_clock_rollback_raises_error():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
        max_clock_rollback_ms=5,
    )

    generator.generate()

    clock.timestamp_ms = 900

    with pytest.raises(ClockRollbackError):
        generator.generate()


# Test worker ID validation
from app.id_generator.exceptions import InvalidWorkerIdError


@pytest.mark.parametrize(
    "worker_id",
    [-1, 1024, 5000],
)
def test_invalid_worker_id_is_rejected(worker_id):
    with pytest.raises(InvalidWorkerIdError):
        SnowflakeGenerator(
            worker_id=worker_id,
            epoch_ms=EPOCH,
        )


# Test different workers
def test_different_workers_generate_different_ids():
    clock = FakeClock(1000)

    worker_1 = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    worker_2 = SnowflakeGenerator(
        worker_id=2,
        epoch_ms=EPOCH,
        clock=clock,
    )

    ids_1 = {worker_1.generate() for _ in range(100)}
    ids_2 = {worker_2.generate() for _ in range(100)}

    assert ids_1.isdisjoint(ids_2)


# concurrency test
from concurrent.futures import ThreadPoolExecutor


def test_concurrent_generation_produces_unique_ids():
    clock = FakeClock(1000)

    generator = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    with ThreadPoolExecutor(max_workers=100) as executor:
        ids = list(
            executor.map(
                lambda _: generator.generate(),
                range(3000),
            )
        )

    assert len(ids) == 3000
    assert len(set(ids)) == 3000


# We should also verify that the IDs are globally unique across workers under concurrent generation.
def test_concurrent_generation_across_workers():
    clock = FakeClock(1000)

    worker_1 = SnowflakeGenerator(
        worker_id=1,
        epoch_ms=EPOCH,
        clock=clock,
    )

    worker_2 = SnowflakeGenerator(
        worker_id=2,
        epoch_ms=EPOCH,
        clock=clock,
    )

    def generate_from_worker(worker):
        return worker.generate()

    with ThreadPoolExecutor(max_workers=100) as executor:
        ids_1 = list(
            executor.map(
                lambda _: generate_from_worker(worker_1),
                range(1000),
            )
        )

        ids_2 = list(
            executor.map(
                lambda _: generate_from_worker(worker_2),
                range(1000),
            )
        )

    all_ids = ids_1 + ids_2

    assert len(all_ids) == 2000
    assert len(set(all_ids)) == 2000
