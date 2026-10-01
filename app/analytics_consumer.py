import logging
import signal
from datetime import UTC
from time import sleep

from cassandra.cluster import NoHostAvailable
from confluent_kafka import Consumer, KafkaError, KafkaException

from app.config.settings import settings
from app.database.cassandra.connection import cassandra_connection
from app.database.cassandra.schema import create_keyspace, create_tables
from app.models.click_event import ClickEvent
from app.repositories.analytics_repository import AnalyticsRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
running = True


def stop(_signum, _frame) -> None:
    global running
    running = False


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for attempt in range(1, settings.startup_attempts + 1):
        try:
            cassandra_connection.connect()
            create_keyspace()
            create_tables()
            break
        except NoHostAvailable:
            cassandra_connection.close()
            if attempt == settings.startup_attempts:
                raise
            logger.warning("Cassandra unavailable; retry %d", attempt)
            sleep(settings.startup_delay_seconds)
    repository = AnalyticsRepository(cassandra_connection.get_session())
    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([settings.kafka_click_topic])
    ttl = settings.analytics_retention_days * 86400
    logger.info("Analytics consumer started")
    try:
        while running:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() != KafkaError._PARTITION_EOF:
                    raise KafkaException(message.error())
                continue
            event = ClickEvent.model_validate_json(message.value())
            clicked_at = event.clicked_at
            if clicked_at.tzinfo is None:
                clicked_at = clicked_at.replace(tzinfo=UTC)
            repository.record(event.event_id, event.short_code, clicked_at, ttl)
            consumer.commit(message=message, asynchronous=False)
    finally:
        consumer.close()
        cassandra_connection.close()


if __name__ == "__main__":
    main()
