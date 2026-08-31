import uuid

from pydantic import BaseModel, ConfigDict

from app.models.campaign import CampaignLeadStatus, CampaignStatus


class CampaignLeadCreate(BaseModel):
    phone_number: str
    context: dict = {}


class CampaignLeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    context: dict
    status: CampaignLeadStatus
    attempts: int
    outcome: str | None


class CampaignCreate(BaseModel):
    name: str
    agent_version_id: uuid.UUID
    leads: list[CampaignLeadCreate]


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_version_id: uuid.UUID
    name: str
    status: CampaignStatus
    dograh_campaign_id: str | None
