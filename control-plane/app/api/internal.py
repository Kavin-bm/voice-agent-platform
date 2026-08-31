"""Endpoints Dograh calls into, never a browser — separate from api/v1's
tenant-JWT auth model. Guarded by a shared secret checked per-request
instead (see Settings.internal_tool_secret / dograh_webhook_secret)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models.agent import AgentVersion
from app.models.call import Call, CallDirection, CallStatus, Recording, Transcript
from app.models.campaign import Campaign, CampaignLead
from app.models.tenant import Tenant
from app.services.dograh_client import fetch_call_artifact
from app.services.search import search_knowledge

router = APIRouter(prefix="/internal/tools", tags=["internal-tools"])
webhooks_router = APIRouter(prefix="/internal/webhooks", tags=["internal-webhooks"])
settings = get_settings()


def require_tool_secret(x_tool_secret: Annotated[str | None, Header()] = None) -> None:
    if x_tool_secret != settings.internal_tool_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tool secret")


def require_webhook_secret(x_webhook_secret: Annotated[str | None, Header()] = None) -> None:
    if x_webhook_secret != settings.dograh_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")


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


class CallCompleteWebhook(BaseModel):
    """Field names match the payload_template baked into the webhook node at
    publish time (providers/adapters/dograh.py) — Jinja renders every value
    as a string even where the source is numeric, so numeric fields arrive
    as strings here and get best-effort parsed, not trusted as JSON numbers."""

    agent_version_id: uuid.UUID
    workflow_run_id: str | None = None
    call_duration_seconds: str | None = None
    call_disposition: str | None = None
    recording_url: str | None = None
    transcript_url: str | None = None
    direction: str | None = None
    dograh_campaign_id: str | None = None
    called_number: str | None = None


@webhooks_router.post(
    "/dograh-call-complete",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_webhook_secret)],
)
async def dograh_call_complete(
    body: CallCompleteWebhook, db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    version = await db.get(AgentVersion, body.agent_version_id)
    if version is None:
        # Don't 404: Dograh's delivery task retries with backoff and dead-
        # letters on repeated failure. A version we can't find is permanent,
        # not transient, but 200/204-ing it avoids a pointless retry loop —
        # log_failure-equivalent visibility is a later concern (Ch. 07: analytics).
        return None

    try:
        duration = int(float(body.call_duration_seconds)) if body.call_duration_seconds else None
    except ValueError:
        duration = None

    # Campaign-dispatched runs set initial_context.direction="outbound"
    # explicitly (confirmed against Dograh's campaign dispatcher source);
    # nothing sets it for an inbound run, so its absence is a real signal.
    # dograh_campaign_id backs that up and lets us resolve the specific
    # CampaignLead this call was for, by matching the dialed number.
    is_outbound = body.direction == "outbound" or bool(
        body.dograh_campaign_id and body.dograh_campaign_id not in ("None", "")
    )

    campaign_lead_id = None
    if is_outbound and body.dograh_campaign_id and body.called_number:
        campaign = (
            await db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == version.tenant_id,
                    Campaign.dograh_campaign_id == body.dograh_campaign_id,
                )
            )
        ).scalar_one_or_none()
        if campaign:
            campaign_lead_id = (
                await db.execute(
                    select(CampaignLead.id).where(
                        CampaignLead.campaign_id == campaign.id,
                        CampaignLead.phone_number == body.called_number,
                    )
                )
            ).scalar_one_or_none()

    call = Call(
        tenant_id=version.tenant_id,
        agent_version_id=version.id,
        campaign_lead_id=campaign_lead_id,
        direction=CallDirection.outbound if is_outbound else CallDirection.inbound,
        status=CallStatus.completed,
        dograh_call_id=body.workflow_run_id,
        duration_sec=duration,
        outcome=body.call_disposition,
    )
    db.add(call)
    await db.flush()

    if body.recording_url:
        db.add(
            Recording(
                tenant_id=version.tenant_id,
                call_id=call.id,
                storage_uri=body.recording_url,
            )
        )

    if body.transcript_url:
        tenant = await db.get(Tenant, version.tenant_id)
        try:
            content = await fetch_call_artifact(tenant, body.transcript_url)
        except Exception as exc:  # noqa: BLE001 - fall back to the URL, don't drop the call record
            content = f"[transcript fetch failed: {exc}] {body.transcript_url}"
        db.add(Transcript(tenant_id=version.tenant_id, call_id=call.id, content=content))

    await db.commit()
    return None
