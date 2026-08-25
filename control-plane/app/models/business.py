from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class Business(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(200))

    # Structured facts (hours, location, services, languages) — PRD section 4:
    # these are configuration, not knowledge, so they're never chunked/RAG'd.
    structured_config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Default target for the transfer_call tool; a Policy can override per
    # escalation category (see Tools & integrations in the plan).
    default_transfer_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
