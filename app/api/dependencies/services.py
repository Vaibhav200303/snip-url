from app.api.dependencies.cassandra import get_cassandra_session
from app.api.dependencies.repositories import get_url_repository
from app.id_generator.short_code import ShortCodeGenerator
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_cache import UrlCache
from app.services.analytics_service import AnalyticsService
from app.services.click_publisher import ClickPublisher
from app.services.redirect_service import RedirectService
from app.services.url_service import UrlService


# Temporary configuration.
# We'll move this to the application container later.
def get_short_code_generator() -> ShortCodeGenerator:
    from app.core.snowflake import snowflake_generator

    return ShortCodeGenerator(snowflake_generator)


def get_url_service() -> UrlService:
    return UrlService(
        repository=get_url_repository(),
        short_code_generator=get_short_code_generator(),
        cache=UrlCache(),
    )


def get_redirect_service() -> RedirectService:
    return RedirectService(
        repository=get_url_repository(),
        cache=UrlCache(),
    )


def get_analytics_service() -> AnalyticsService:
    repository = get_url_repository()
    return AnalyticsService(
        urls=repository,
        analytics=AnalyticsRepository(get_cassandra_session()),
    )


def get_click_publisher() -> ClickPublisher:
    from app.main import click_publisher

    return click_publisher
