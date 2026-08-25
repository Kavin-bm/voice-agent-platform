import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import Timestamped, UUIDPk


class AgentTemplate(Base, UUIDPk, Timestamped):
    """Generic role template (Receptionist, Sales, Support, Booking, Lead
    Qualification). Global seed data, not tenant-scoped — loaded from
    templates/*.yaml at startup, see scripts/onboard_client.py."""

    __tablename__ = "agent_templates"

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    base_prompt: Mapped[str] = mapped_column(String)
    default_policies: Mapped[list] = mapped_column(JSON, default=list)
    default_tools: Mapped[list] = mapped_column(JSON, default=list)


class VerticalPack(Base, UUIDPk, Timestamped):
    """Industry overlay on a template (PRD section 6) — e.g. Receptionist +
    Dental. Merged on top of the base template at compile time in
    agent_compiler.py. Global seed data; new packs are drafted fast with
    scripts/scaffold_vertical.py and reviewed before use."""

    __tablename__ = "vertical_packs"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_templates.id", ondelete="CASCADE")
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    prompt_additions: Mapped[str] = mapped_column(String, default="")
    extra_policies: Mapped[list] = mapped_column(JSON, default=list)
    extra_tools: Mapped[list] = mapped_column(JSON, default=list)
    default_provider_stack: Mapped[dict] = mapped_column(JSON, default=dict)
