import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class KnowledgeSource(Base, UUIDPk, Timestamped, TenantScoped):
    """Groups documents under a business (e.g. 'Dental Clinic FAQs')."""

    __tablename__ = "knowledge_sources"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))


class Document(Base, UUIDPk, Timestamped, TenantScoped):
    """We're the system of record (ownership, our own MinIO copy for
    portability across a future runtime swap); the actual parse/chunk/embed/
    search is proxied to Dograh's knowledge-base (see the architecture-pivot
    note in the plan) — dograh_document_uuid is that mapping, and status
    mirrors Dograh's own processing_status. No local Chunk/embedding table:
    reimplementing that pipeline would just duplicate what Dograh already
    does, at the cost of an extra retrieval hop during a live call."""

    __tablename__ = "documents"

    knowledge_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE")
    )
    source_type: Mapped[str] = mapped_column(String(20))  # pdf | docx | xlsx | txt | url
    source_uri: Mapped[str] = mapped_column(String)  # our MinIO object key or source URL
    dograh_document_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.pending
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
