from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.template import AgentTemplate, VerticalPack
from app.schemas.template import AgentTemplateRead, VerticalPackRead

# Global seed data, not tenant-scoped — any authenticated user can browse
# available templates/vertical packs when creating an agent.
router = APIRouter(
    prefix="/templates", tags=["templates"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[AgentTemplateRead])
async def list_templates(db: Annotated[AsyncSession, Depends(get_db)]) -> list[AgentTemplateRead]:
    result = await db.execute(select(AgentTemplate))
    return list(result.scalars().all())


@router.get("/{template_id}/vertical-packs", response_model=list[VerticalPackRead])
async def list_vertical_packs(
    template_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[VerticalPackRead]:
    result = await db.execute(select(VerticalPack).where(VerticalPack.template_id == template_id))
    return list(result.scalars().all())
