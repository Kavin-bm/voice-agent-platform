import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class Policy(Base, UUIDPk, Timestamped, TenantScoped):
    """A rule governing what the agent can/cannot do — injected as global
    instructions on compile, never RAG'd (PRD section 4). escalation_target
    lets a category of request route to a different transfer number than
    Business.default_transfer_number."""

    __tablename__ = "policies"

    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(100))
    rule_text: Mapped[str] = mapped_column(Text)
    escalation_target: Mapped[str | None] = mapped_column(String(32), nullable=True)
