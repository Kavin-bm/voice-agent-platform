import uuid

from pydantic import BaseModel


class OnboardPolicy(BaseModel):
    category: str
    rule_text: str
    escalation_target: str | None = None


class OnboardPhoneNumber(BaseModel):
    number: str
    provider: str
    country_code: str | None = None


class OnboardRequest(BaseModel):
    """One call for the operator flow that matters: signed client -> live
    draft agent. Chains business -> agent -> version -> policies ->
    knowledge (by URL) -> compile -> publish, and optionally binds a phone
    number if one's already provisioned on the provider. Anything skippable
    (policies, knowledge_document_urls, phone_number) defaults to empty/None
    so this also works for "just get me a draft to look at"."""

    business_name: str
    structured_config: dict = {}
    default_transfer_number: str | None = None

    template_id: uuid.UUID
    vertical_pack_id: uuid.UUID | None = None
    agent_name: str
    voice_config: dict = {}

    policies: list[OnboardPolicy] = []
    knowledge_document_urls: list[str] = []

    publish: bool = True
    phone_number: OnboardPhoneNumber | None = None


class OnboardResponse(BaseModel):
    business_id: uuid.UUID
    agent_id: uuid.UUID
    agent_version_id: uuid.UUID
    dograh_workflow_id: str | None
    phone_number_id: uuid.UUID | None
