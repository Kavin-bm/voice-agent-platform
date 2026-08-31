import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.agent import AgentVersion, AgentVersionStatus
from app.models.campaign import Campaign, CampaignLead, CampaignStatus
from app.models.tenant import Tenant
from app.schemas.campaign import CampaignCreate, CampaignLeadRead, CampaignRead
from app.services.campaign_csv import build_leads_csv
from app.services.dograh_client import (
    create_dograh_campaign,
    get_dograh_campaign_progress,
    pause_dograh_campaign,
    resume_dograh_campaign,
    start_dograh_campaign,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


async def _get_owned_campaign(campaign_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None or campaign.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignRead:
    version = await db.get(AgentVersion, body.agent_version_id)
    if version is None or version.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
    if version.status != AgentVersionStatus.published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a published version can run a campaign",
        )
    if not body.leads:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one lead is required")

    campaign = Campaign(tenant_id=tenant_id, agent_version_id=version.id, name=body.name)
    db.add(campaign)
    await db.flush()

    for lead in body.leads:
        db.add(
            CampaignLead(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                phone_number=lead.phone_number,
                context=lead.context,
            )
        )

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CampaignRead]:
    result = await db.execute(select(Campaign).where(Campaign.tenant_id == tenant_id))
    return list(result.scalars().all())


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignRead:
    return await _get_owned_campaign(campaign_id, tenant_id, db)


@router.get("/{campaign_id}/leads", response_model=list[CampaignLeadRead])
async def list_campaign_leads(
    campaign_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CampaignLeadRead]:
    await _get_owned_campaign(campaign_id, tenant_id, db)
    result = await db.execute(select(CampaignLead).where(CampaignLead.campaign_id == campaign_id))
    return list(result.scalars().all())


@router.post("/{campaign_id}/launch", response_model=CampaignRead)
async def launch_campaign(
    campaign_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignRead:
    """Uploads the lead list to Dograh, creates the campaign there, and
    starts it — all delegated, we don't run our own dialer. Will fail
    cleanly (502, see DograhClientError) if the tenant's Dograh org has no
    telephony configuration at all; that's Dograh's own gate, not ours.

    Idempotent on retry: if create+upload already succeeded and only start
    failed (e.g. telephony wasn't configured yet), a second call skips
    straight to start instead of uploading the CSV and creating a second
    Dograh campaign — found this gap by actually hitting it live."""
    campaign = await _get_owned_campaign(campaign_id, tenant_id, db)
    tenant = await db.get(Tenant, tenant_id)

    if not campaign.dograh_campaign_id:
        version = await db.get(AgentVersion, campaign.agent_version_id)
        if not version.dograh_workflow_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Agent version has no published workflow"
            )

        leads = list(
            (await db.execute(select(CampaignLead).where(CampaignLead.campaign_id == campaign_id)))
            .scalars()
            .all()
        )
        csv_bytes = build_leads_csv(leads)
        campaign.dograh_campaign_id = await create_dograh_campaign(
            tenant, campaign.name, version.dograh_workflow_id, csv_bytes
        )
        await db.commit()

    await start_dograh_campaign(tenant, campaign.dograh_campaign_id)
    campaign.status = CampaignStatus.running
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/pause", response_model=CampaignRead)
async def pause_campaign(
    campaign_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignRead:
    campaign = await _get_owned_campaign(campaign_id, tenant_id, db)
    if not campaign.dograh_campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign hasn't been launched")
    tenant = await db.get(Tenant, tenant_id)
    await pause_dograh_campaign(tenant, campaign.dograh_campaign_id)
    campaign.status = CampaignStatus.paused
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/resume", response_model=CampaignRead)
async def resume_campaign(
    campaign_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignRead:
    campaign = await _get_owned_campaign(campaign_id, tenant_id, db)
    if not campaign.dograh_campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign hasn't been launched")
    tenant = await db.get(Tenant, tenant_id)
    await resume_dograh_campaign(tenant, campaign.dograh_campaign_id)
    campaign.status = CampaignStatus.running
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}/progress")
async def campaign_progress(
    campaign_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Live-proxies Dograh's own progress endpoint rather than mirroring
    counts into our DB — one less thing to keep in sync, and this is exactly
    the kind of number that's only useful fresh."""
    campaign = await _get_owned_campaign(campaign_id, tenant_id, db)
    if not campaign.dograh_campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign hasn't been launched")
    tenant = await db.get(Tenant, tenant_id)
    return await get_dograh_campaign_progress(tenant, campaign.dograh_campaign_id)
