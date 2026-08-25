import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"


class Campaign(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "campaigns"

    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id")
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"), default=CampaignStatus.draft
    )
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CampaignLeadStatus(str, enum.Enum):
    pending = "pending"
    dialing = "dialing"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"


class CampaignLead(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "campaign_leads"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    phone_number: Mapped[str] = mapped_column(String(32))
    context: Mapped[dict] = mapped_column(JSON, default=dict)  # lead/customer context injection
    status: Mapped[CampaignLeadStatus] = mapped_column(
        Enum(CampaignLeadStatus, name="campaign_lead_status"), default=CampaignLeadStatus.pending
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
