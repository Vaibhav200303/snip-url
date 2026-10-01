from cassandra.cluster import Session

from app.database.cassandra.connection import cassandra_connection


def get_cassandra_session() -> Session:
    return cassandra_connection.get_session()