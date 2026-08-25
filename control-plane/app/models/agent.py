import enum
import uuid

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class Agent(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "agents"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_templates.id")
    )
    vertical_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vertical_packs.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))


class AgentVersionStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class AgentVersion(Base, UUIDPk, Timestamped, TenantScoped):
    """One buildable/publishable snapshot of an agent. Draft versions are
    exercised via the test-call API before publish flips the live
    PhoneNumber binding — see Agent versioning & safe publish in the plan."""

    __tablename__ = "agent_versions"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[AgentVersionStatus] = mapped_column(
        Enum(AgentVersionStatus, name="agent_version_status"), default=AgentVersionStatus.draft
    )

    # Full neutral spec produced by agent_compiler.py (template + vertical
    # pack + business + knowledge refs + policies + tools + voice + model).
    compiled_spec: Mapped[dict] = mapped_column(JSON, default=dict)

    # Conversational-style knobs: persona/tone, backchannel, interruption
    # sensitivity, Sarvam emotion-control param — see Voice quality & latency.
    voice_config: Mapped[dict] = mapped_column(JSON, default=dict)
    model_config_: Mapped[dict] = mapped_column("model_config", JSON, default=dict)

    # Set once pushed to the runtime; adapters/dograh.py owns this identifier,
    # nothing else in the codebase should interpret it.
    dograh_workflow_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
