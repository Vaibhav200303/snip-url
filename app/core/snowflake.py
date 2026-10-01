from app.config.settings import settings
from app.id_generator.snowflake import SnowflakeGenerator

snowflake_generator = SnowflakeGenerator(
    worker_id=settings.snowflake_worker_id,
    epoch_ms=settings.snowflake_epoch_ms,
    max_clock_rollback_ms=settings.snowflake_max_clock_rollback_ms,
)