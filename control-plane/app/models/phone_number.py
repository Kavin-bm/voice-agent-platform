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
    # ISO 3166-1 alpha-2, e.g. "IN" — Dograh needs this alongside the number
    # to normalize the address; only PSTN providers require it.
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Dograh's own numeric id for this number, once bind_phone_number has
    # pushed it there — None means "not synced to Dograh yet". Lets rebinds
    # PUT the existing row instead of creating a duplicate.
    dograh_phone_number_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Publishing an AgentVersion atomically swaps this — the previous version
    # stays in the DB (not deleted) so rollback is just republishing it.
    bound_agent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id"), nullable=True
    )
