from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ClickEvent(BaseModel):
    event_id: UUID
    short_code: str
    clicked_at: datetime
