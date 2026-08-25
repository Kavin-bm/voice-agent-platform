import uuid

from pydantic import BaseModel, ConfigDict

from app.models.agent import AgentVersionStatus


class AgentCreate(BaseModel):
    business_id: uuid.UUID
    template_id: uuid.UUID
    vertical_pack_id: uuid.UUID | None = None
    name: str


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    template_id: uuid.UUID
    vertical_pack_id: uuid.UUID | None
    name: str


class AgentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    version_number: int
    status: AgentVersionStatus
    compiled_spec: dict
    voice_config: dict
    dograh_workflow_id: str | None
