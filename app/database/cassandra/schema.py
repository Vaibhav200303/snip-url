import hashlib
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
    session.execute(
        """
        CREATE TABLE IF NOT EXISTS urls_by_destination (
            destination_hash text,
            created_at timestamp,
            short_code text,
            long_url text,
            expiration_at timestamp,
            is_enabled boolean,
            PRIMARY KEY ((destination_hash), created_at, short_code)
        ) WITH CLUSTERING ORDER BY (created_at DESC, short_code ASC)
        """
    )
    _backfill_destination_index()
    logger.info("Cassandra schema is ready")


def _backfill_destination_index() -> None:
    """Populate the lookup table for links created before the table existed.

    This project intentionally uses an idempotent development bootstrap rather
    than a general-purpose Cassandra migration framework.
    """
    session = cassandra_connection.get_session()
    insert = session.prepare(
        "INSERT INTO urls_by_destination "
        "(destination_hash,created_at,short_code,long_url,expiration_at,is_enabled) "
        "VALUES (?,?,?,?,?,?)"
    )
    rows = session.execute(
        "SELECT created_at,short_code,long_url,expiration_at,is_enabled "
        "FROM urls_by_created WHERE bucket='all'"
    )
    count = 0
    for row in rows:
        destination_hash = hashlib.sha256(row.long_url.encode("utf-8")).hexdigest()
        session.execute(
            insert,
            [
                destination_hash,
                row.created_at,
                row.short_code,
                row.long_url,
                row.expiration_at,
                row.is_enabled,
            ],
        )
        count += 1
    if count:
        logger.info("Backfilled destination lookup index", extra={"rows": count})
