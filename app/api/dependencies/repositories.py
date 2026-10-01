from app.api.dependencies.cassandra import get_cassandra_session
from app.repositories.url_repository import UrlRepository


def get_url_repository() -> UrlRepository:
    return UrlRepository(get_cassandra_session())
