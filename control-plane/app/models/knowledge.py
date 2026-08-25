import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk

# Sarvam / OpenAI-compatible embedding models used by services/ingestion/embedder.py
# both output 1536-dim vectors; fixed here rather than made configurable
# because MVP only ever runs one embedding model at a time.
EMBEDDING_DIM = 1536


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
    __tablename__ = "documents"

    knowledge_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE")
    )
    source_type: Mapped[str] = mapped_column(String(20))  # pdf | docx | xlsx | txt | url
    source_uri: Mapped[str] = mapped_column(String)  # object-store key or source URL
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.pending
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Chunk(Base, UUIDPk, Timestamped, TenantScoped):
    """Retrieved dynamically via the search_knowledge tool during a call —
    never inserted directly into the prompt (PRD section 4)."""

    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
