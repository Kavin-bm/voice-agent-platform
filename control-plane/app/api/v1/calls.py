import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.call import Call, Recording, Transcript
from app.schemas.call import CallDetail, CallRead, RecordingRead, TranscriptRead

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=list[CallRead])
async def list_calls(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CallRead]:
    result = await db.execute(
        select(Call).where(Call.tenant_id == tenant_id).order_by(Call.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{call_id}", response_model=CallDetail)
async def get_call(
    call_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CallDetail:
    call = await db.get(Call, call_id)
    if call is None or call.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    transcript = (
        await db.execute(select(Transcript).where(Transcript.call_id == call_id))
    ).scalars().first()
    recording = (
        await db.execute(select(Recording).where(Recording.call_id == call_id))
    ).scalars().first()

    return CallDetail(
        **CallRead.model_validate(call).model_dump(),
        transcript=TranscriptRead.model_validate(transcript) if transcript else None,
        recording=RecordingRead.model_validate(recording) if recording else None,
    )
