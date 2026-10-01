import logging

from app.database.cassandra.connection import cassandra_connection

logger = logging.getLogger(__name__)


def create_keyspace() -> None:
    session = cassandra_connection.get_session()

    session.execute(
        """
        CREATE KEYSPACE IF NOT EXISTS snipurl
        WITH replication = {
            'class': 'SimpleStrategy',
            'replication_factor': 1
        }
        """
    )


def _add_column_if_missing(table: str, definition: str) -> None:
    session = cassandra_connection.get_session()
    column = definition.split()[0]
    exists = session.execute(
        "SELECT column_name FROM system_schema.columns "
        "WHERE keyspace_name='snipurl' AND table_name=%s AND column_name=%s",
        [table, column],
    ).one()
    if exists is None:
        session.execute(f"ALTER TABLE {table} ADD {definition}")


def create_tables() -> None:
    session = cassandra_connection.get_session()

    session.set_keyspace("snipurl")
    session.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            short_code text PRIMARY KEY,
            long_url text,
            created_at timestamp,
            expiration_at timestamp,
            is_custom boolean,
            is_enabled boolean
        )
        """
    )
    _add_column_if_missing("urls", "expiration_at timestamp")
    _add_column_if_missing("urls", "is_enabled boolean")
    session.execute(
        """
        CREATE TABLE IF NOT EXISTS urls_by_created (
            bucket text,
            created_at timestamp,
            short_code text,
            long_url text,
            expiration_at timestamp,
            is_custom boolean,
            is_enabled boolean,
            PRIMARY KEY ((bucket), created_at, short_code)
        ) WITH CLUSTERING ORDER BY (created_at DESC, short_code ASC)
        """
    )
    session.execute(
        """
        CREATE TABLE IF NOT EXISTS click_events_by_day (
            short_code text,
            event_date date,
            clicked_at timestamp,
            event_id uuid,
            PRIMARY KEY ((short_code, event_date), clicked_at, event_id)
        ) WITH CLUSTERING ORDER BY (clicked_at DESC, event_id ASC)
        """
    )
    logger.info("Cassandra schema is ready")
