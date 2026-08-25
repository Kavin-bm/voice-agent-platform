import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class CallDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class CallStatus(str, enum.Enum):
    ringing = "ringing"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    no_answer = "no_answer"


class Call(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "calls"

    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id")
    )
    phone_number_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("phone_numbers.id"), nullable=True
    )
    campaign_lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_leads.id"), nullable=True
    )
    dograh_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    direction: Mapped[CallDirection] = mapped_column(Enum(CallDirection, name="call_direction"))
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, name="call_status"), default=CallStatus.ringing
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Caller stops talking -> agent audio starts, milliseconds. Target p50
    # <800ms / p95 <1.5s — see Voice quality & latency in the plan. Populated
    # from Dograh's webhook event timestamps once that payload shape is
    # confirmed against a real call (flagged as a risk in the plan).
    first_response_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class Transcript(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "transcripts"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)  # full turn-by-turn transcript, speaker-tagged


class Recording(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "recordings"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"))
    storage_uri: Mapped[str] = mapped_column(String)  # MinIO/S3 object key
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
