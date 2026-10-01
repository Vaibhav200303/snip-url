from datetime import date, datetime, timedelta
from uuid import UUID

from cassandra.cluster import Session


class AnalyticsRepository:
    def __init__(self, session: Session):
        self.session = session
        self._insert = session.prepare(
            "INSERT INTO click_events_by_day "
            "(short_code,event_date,clicked_at,event_id) VALUES (?,?,?,?) USING TTL ?"
        )
        self._count = session.prepare(
            "SELECT COUNT(*) AS clicks FROM click_events_by_day "
            "WHERE short_code=? AND event_date=?"
        )

    def record(
        self,
        event_id: UUID,
        short_code: str,
        clicked_at: datetime,
        ttl_seconds: int,
    ) -> None:
        self.session.execute(
            self._insert,
            [short_code, clicked_at.date(), clicked_at, event_id, ttl_seconds],
        )

    def daily_counts(self, short_code: str, start: date, end: date):
        current = start
        counts: list[dict] = []
        while current <= end:
            row = self.session.execute(self._count, [short_code, current]).one()
            counts.append({"date": current, "clicks": int(row.clicks)})
            current += timedelta(days=1)
        return counts
