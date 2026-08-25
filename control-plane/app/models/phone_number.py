import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class PhoneNumber(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "phone_numbers"

    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(50))  # exotel | plivo | twilio | telnyx

    # Publishing an AgentVersion atomically swaps this — the previous version
    # stays in the DB (not deleted) so rollback is just republishing it.
    bound_agent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id"), nullable=True
    )
