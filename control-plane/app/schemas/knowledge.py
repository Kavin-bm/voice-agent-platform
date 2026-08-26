import uuid

from pydantic import BaseModel, ConfigDict

from app.models.knowledge import DocumentStatus


class KnowledgeSourceCreate(BaseModel):
    business_id: uuid.UUID
    name: str


class KnowledgeSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str


class DocumentUrlCreate(BaseModel):
    url: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_source_id: uuid.UUID
    source_type: str
    status: DocumentStatus
    error: str | None
