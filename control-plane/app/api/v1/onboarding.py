import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.agents import compile_version, create_agent, create_agent_version, publish_version
from app.api.v1.businesses import create_business
from app.api.v1.knowledge import add_document_from_url, create_knowledge_source
from app.api.v1.phone_numbers import bind_phone_number, create_phone_number
from app.api.v1.policies import create_policy
from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.schemas.agent import AgentCreate
from app.schemas.business import BusinessCreate
from app.schemas.knowledge import DocumentUrlCreate, KnowledgeSourceCreate
from app.schemas.onboarding import OnboardRequest, OnboardResponse
from app.schemas.phone_number import PhoneNumberBind, PhoneNumberCreate
from app.schemas.policy import PolicyCreate

router = APIRouter(prefix="/onboard", tags=["onboarding"])


@router.post("", response_model=OnboardResponse)
async def onboard_client(
    body: OnboardRequest,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardResponse:
    """The one-call version of "Composing an agent" in the README: chains
    the same endpoints below it calls directly (not by re-deriving their
    logic), so this can never drift from what those endpoints actually do.
    Every step after business creation depends on the previous one's id,
    so this is deliberately sequential, not parallelized."""

    business = await create_business(
        BusinessCreate(
            name=body.business_name,
            structured_config=body.structured_config,
            default_transfer_number=body.default_transfer_number,
        ),
        tenant_id,
        db,
    )

    agent = await create_agent(
        AgentCreate(
            business_id=business.id,
            template_id=body.template_id,
            vertical_pack_id=body.vertical_pack_id,
            name=body.agent_name,
        ),
        tenant_id,
        db,
    )
    version = await create_agent_version(agent.id, tenant_id, db)
    if body.voice_config:
        version.voice_config = body.voice_config
        await db.commit()
        await db.refresh(version)

    for policy in body.policies:
        await create_policy(
            agent.id,
            version.id,
            PolicyCreate(
                category=policy.category,
                rule_text=policy.rule_text,
                escalation_target=policy.escalation_target,
            ),
            tenant_id,
            db,
        )

    if body.knowledge_document_urls:
        knowledge_source = await create_knowledge_source(
            KnowledgeSourceCreate(business_id=business.id, name=f"{business.name} documents"),
            tenant_id,
            db,
        )
        for url in body.knowledge_document_urls:
            await add_document_from_url(knowledge_source.id, DocumentUrlCreate(url=url), tenant_id, db)

    version = await compile_version(agent.id, version.id, tenant_id, db)

    if body.publish:
        version = await publish_version(agent.id, version.id, tenant_id, db)

    phone_number_id = None
    if body.phone_number and body.publish:
        phone = await create_phone_number(
            PhoneNumberCreate(
                number=body.phone_number.number,
                provider=body.phone_number.provider,
                country_code=body.phone_number.country_code,
            ),
            tenant_id,
            db,
        )
        phone = await bind_phone_number(
            phone.id, PhoneNumberBind(agent_version_id=version.id), tenant_id, db
        )
        phone_number_id = phone.id

    return OnboardResponse(
        business_id=business.id,
        agent_id=agent.id,
        agent_version_id=version.id,
        dograh_workflow_id=version.dograh_workflow_id,
        phone_number_id=phone_number_id,
    )
