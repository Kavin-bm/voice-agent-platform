import uuid

from pydantic import BaseModel, ConfigDict


class PolicyCreate(BaseModel):
    category: str
    rule_text: str
    escalation_target: str | None = None


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_version_id: uuid.UUID
    category: str
    rule_text: str
    escalation_target: str | None
