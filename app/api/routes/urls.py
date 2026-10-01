from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.dependencies.security import require_admin_api_key
from app.api.dependencies.services import (
    get_analytics_service,
    get_click_publisher,
    get_redirect_service,
    get_url_service,
)
from app.config.settings import settings
from app.schemas.url import (
    AnalyticsResponse,
    ShortenUrlRequest,
    ShortenUrlResponse,
    UpdateUrlRequest,
    UrlListResponse,
    UrlResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.click_publisher import ClickPublisher
from app.services.rate_limiter import RateLimiter
from app.services.redirect_service import RedirectService
from app.services.url_service import UrlService

api_router = APIRouter(prefix="/api/v1/urls", tags=["URLs"])
redirect_router = APIRouter(tags=["Redirects"])
rate_limiter = RateLimiter()


def _identity(request: Request) -> str:
    # Nginx overwrites this header with the actual peer address. Direct access
    # to the API is bound to loopback only in Compose.
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


@api_router.post("", response_model=ShortenUrlResponse, status_code=201)
def shorten_url(
    payload: ShortenUrlRequest,
    request: Request,
    service: UrlService = Depends(get_url_service),
):
    rate_limiter.check(
        "create",
        _identity(request),
        settings.create_rate_limit,
        settings.rate_limit_window_seconds,
    )
    return service.shorten(payload)


@api_router.get(
    "",
    response_model=UrlListResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def list_urls(
    limit: int = Query(default=20, ge=1),
    cursor: str | None = None,
    service: UrlService = Depends(get_url_service),
):
    return service.list(min(limit, settings.max_page_size), cursor)


@api_router.get(
    "/{short_code}",
    response_model=UrlResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def get_url(short_code: str, service: UrlService = Depends(get_url_service)):
    return service.get(short_code)


@api_router.patch(
    "/{short_code}",
    response_model=UrlResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def update_url(
    short_code: str,
    payload: UpdateUrlRequest,
    service: UrlService = Depends(get_url_service),
):
    return service.update(short_code, payload)


@api_router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_api_key)],
)
def delete_url(short_code: str, service: UrlService = Depends(get_url_service)):
    service.delete(short_code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api_router.get(
    "/{short_code}/analytics",
    response_model=AnalyticsResponse,
    dependencies=[Depends(require_admin_api_key)],
)
def get_analytics(
    short_code: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    service: AnalyticsService = Depends(get_analytics_service),
):
    end = to_date or datetime.now(UTC).date()
    start = from_date or end - timedelta(days=29)
    return service.get(short_code, start, end)


@redirect_router.get("/{short_code}", include_in_schema=False)
def redirect_url(
    short_code: str,
    request: Request,
    service: RedirectService = Depends(get_redirect_service),
    publisher: ClickPublisher = Depends(get_click_publisher),
):
    rate_limiter.check(
        "redirect",
        _identity(request),
        settings.redirect_rate_limit,
        settings.rate_limit_window_seconds,
    )
    long_url = service.get_long_url(short_code)
    publisher.publish(short_code)
    return RedirectResponse(url=long_url, status_code=302)
