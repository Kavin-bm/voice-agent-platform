import enum
import uuid

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import Timestamped, UUIDPk


class ToolType(str, enum.Enum):
    built_in = "built_in"
    webhook = "webhook"


class Tool(Base, UUIDPk, Timestamped):
    """tenant_id is nullable: built-in tools (search_knowledge,
    book_appointment, create_lead, transfer_call, end_call) are global seed
    rows shared by every tenant. webhook tools are tenant-defined — url,
    method, auth, param schema all live in config — so booking backends and
    CRM updates need zero bespoke integration code (see Tools &
    integrations in the plan)."""

    __tablename__ = "tools"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[ToolType] = mapped_column(Enum(ToolType, name="tool_type"))
    name: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentVersionTool(Base, UUIDPk):
    __tablename__ = "agent_version_tools"

    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id", ondelete="CASCADE")
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tools.id"))
