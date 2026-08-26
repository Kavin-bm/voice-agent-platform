import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.agent import Agent, AgentVersion
from app.models.business import Business
from app.models.template import AgentTemplate, VerticalPack
from app.schemas.agent import AgentCreate, AgentRead, AgentVersionRead
from app.services.agent_compiler import compile_agent_version

router = APIRouter(prefix="/agents", tags=["agents"])


async def _get_owned_agent(
    agent_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> Agent:
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRead:
    business = await db.get(Business, body.business_id)
    if business is None or business.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    template = await db.get(AgentTemplate, body.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    if body.vertical_pack_id is not None:
        pack = await db.get(VerticalPack, body.vertical_pack_id)
        if pack is None or pack.template_id != body.template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vertical pack does not belong to the given template",
            )

    agent = Agent(tenant_id=tenant_id, **body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentRead])
async def list_agents(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentRead]:
    result = await db.execute(select(Agent).where(Agent.tenant_id == tenant_id))
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRead:
    return await _get_owned_agent(agent_id, tenant_id, db)


@router.post(
    "/{agent_id}/versions", response_model=AgentVersionRead, status_code=status.HTTP_201_CREATED
)
async def create_agent_version(
    agent_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentVersionRead:
    await _get_owned_agent(agent_id, tenant_id, db)

    next_number = (
        await db.execute(
            select(func.coalesce(func.max(AgentVersion.version_number), 0) + 1).where(
                AgentVersion.agent_id == agent_id
            )
        )
    ).scalar_one()

    # compiled_spec/voice_config start empty — filled by POST
    # /agents/{id}/versions/{version_id}/compile (see agent_compiler.py)
    # once policies and knowledge sources exist for this agent.
    version = AgentVersion(tenant_id=tenant_id, agent_id=agent_id, version_number=next_number)
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


@router.get("/{agent_id}/versions", response_model=list[AgentVersionRead])
async def list_agent_versions(
    agent_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentVersionRead]:
    await _get_owned_agent(agent_id, tenant_id, db)
    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version_number)
    )
    return list(result.scalars().all())


async def _get_owned_version(
    agent_id: uuid.UUID, version_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> AgentVersion:
    version = await db.get(AgentVersion, version_id)
    if version is None or version.tenant_id != tenant_id or version.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
    return version


@router.post("/{agent_id}/versions/{version_id}/compile", response_model=AgentVersionRead)
async def compile_version(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentVersionRead:
    """Assembles template+vertical pack+business+knowledge+policies+tools+
    voice into AgentVersion.compiled_spec — the neutral spec adapters/
    dograh.py later translates into a runtime workflow. Re-running this
    after editing policies/business config refreshes the draft; it never
    touches a published version's live binding."""
    version = await _get_owned_version(agent_id, version_id, tenant_id, db)
    await compile_agent_version(db, version)
    return version
