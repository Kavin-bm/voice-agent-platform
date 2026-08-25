import uuid

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class UsageEvent(Base, UUIDPk, Timestamped, TenantScoped):
    """Feeds future metered/overage billing without a schema change; MVP just
    records it (platform doesn't resell minutes — see Credentials & tenant
    isolation in the plan)."""

    __tablename__ = "usage_events"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"))
    minutes: Mapped[float] = mapped_column(Float)
