"""Endpoints Dograh calls into, never a browser — separate from api/v1's
tenant-JWT auth model. Guarded by a shared secret checked per-request
instead (see Settings.internal_tool_secret)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.services.search import search_knowledge

router = APIRouter(prefix="/internal/tools", tags=["internal-tools"])
settings = get_settings()


def require_tool_secret(x_tool_secret: Annotated[str | None, Header()] = None) -> None:
    if x_tool_secret != settings.internal_tool_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tool secret")


class SearchKnowledgeRequest(BaseModel):
    query: str
    business_id: uuid.UUID


class SearchKnowledgeResponse(BaseModel):
    results: list[str]
    error: str | None = None


@router.post(
    "/search-knowledge",
    response_model=SearchKnowledgeResponse,
    dependencies=[Depends(require_tool_secret)],
)
async def search_knowledge_tool(
    body: SearchKnowledgeRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> SearchKnowledgeResponse:
    """Always 200s, even on failure (e.g. tenant hasn't configured an
    OpenAI credential yet) — this runs mid-call, and a hard error here
    would surface as a broken tool call to the caller rather than the
    agent just gracefully not having an answer."""
    try:
        results = await search_knowledge(db, body.business_id, body.query)
        return SearchKnowledgeResponse(results=results)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        return SearchKnowledgeResponse(results=[], error=str(exc))
