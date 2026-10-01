import logging
from datetime import UTC, datetime
from uuid import uuid4

from confluent_kafka import Producer

from app.config.settings import settings
from app.models.click_event import ClickEvent

logger = logging.getLogger(__name__)


class ClickPublisher:
    def __init__(self) -> None:
        self.producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})

    def publish(self, short_code: str) -> None:
        event = ClickEvent(
            event_id=uuid4(), short_code=short_code, clicked_at=datetime.now(UTC)
        )
        try:
            self.producer.produce(
                settings.kafka_click_topic,
                key=short_code,
                value=event.model_dump_json(),
                on_delivery=self._delivery_report,
            )
            self.producer.poll(0)
        except BufferError:
            logger.warning("Kafka producer queue is full; click event dropped")

    @staticmethod
    def _delivery_report(error, _message) -> None:
        if error:
            logger.warning("Click event delivery failed: %s", error)

    def close(self) -> None:
        remaining = self.producer.flush(5)
        if remaining:
            logger.warning("Kafka producer closed with %d undelivered events", remaining)
