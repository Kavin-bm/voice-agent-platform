import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.agent import AgentVersion
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyRead

router = APIRouter(prefix="/agents/{agent_id}/versions/{version_id}/policies", tags=["policies"])


async def _get_owned_version(
    agent_id: uuid.UUID, version_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> AgentVersion:
    version = await db.get(AgentVersion, version_id)
    if version is None or version.tenant_id != tenant_id or version.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
    return version


@router.post("", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def create_policy(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    body: PolicyCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRead:
    await _get_owned_version(agent_id, version_id, tenant_id, db)
    policy = Policy(tenant_id=tenant_id, agent_version_id=version_id, **body.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("", response_model=list[PolicyRead])
async def list_policies(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyRead]:
    await _get_owned_version(agent_id, version_id, tenant_id, db)
    result = await db.execute(select(Policy).where(Policy.agent_version_id == version_id))
    return list(result.scalars().all())


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    policy_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await _get_owned_version(agent_id, version_id, tenant_id, db)
    policy = await db.get(Policy, policy_id)
    if policy is None or policy.agent_version_id != version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await db.delete(policy)
    await db.commit()
