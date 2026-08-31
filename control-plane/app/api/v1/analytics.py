import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.agent import Agent, AgentVersion
from app.models.call import Call
from app.schemas.analytics import CallAnalyticsResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _percentile_cont(fraction: float, column):
    return func.percentile_cont(fraction).within_group(column)


@router.get("/calls", response_model=CallAnalyticsResponse)
async def call_analytics(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: uuid.UUID | None = None,
    template_id: uuid.UUID | None = None,
) -> CallAnalyticsResponse:
    """Aggregates in Postgres (percentile_cont, group-by counts) rather than
    pulling every Call row into Python — this is a query that should stay
    cheap as call volume grows, not a place to optimize later."""

    def base_query() -> Select:
        query = select(Call).where(Call.tenant_id == tenant_id)
        if agent_id is not None or template_id is not None:
            query = query.join(AgentVersion, Call.agent_version_id == AgentVersion.id)
            if agent_id is not None:
                query = query.where(AgentVersion.agent_id == agent_id)
            if template_id is not None:
                query = query.join(Agent, AgentVersion.agent_id == Agent.id).where(
                    Agent.template_id == template_id
                )
        return query

    total = (await db.execute(base_query().with_only_columns(func.count(Call.id)))).scalar_one()

    direction_counts = (
        await db.execute(
            base_query().with_only_columns(Call.direction, func.count()).group_by(Call.direction)
        )
    ).all()
    status_counts = (
        await db.execute(base_query().with_only_columns(Call.status, func.count()).group_by(Call.status))
    ).all()
    outcome_counts = (
        await db.execute(
            base_query()
            .with_only_columns(Call.outcome, func.count())
            .where(Call.outcome.is_not(None))
            .group_by(Call.outcome)
        )
    ).all()

    duration_p50, duration_p95 = (
        await db.execute(
            base_query()
            .with_only_columns(
                _percentile_cont(0.5, Call.duration_sec), _percentile_cont(0.95, Call.duration_sec)
            )
            .where(Call.duration_sec.is_not(None))
        )
    ).one()

    latency_p50, latency_p95 = (
        await db.execute(
            base_query()
            .with_only_columns(
                _percentile_cont(0.5, Call.first_response_latency_ms),
                _percentile_cont(0.95, Call.first_response_latency_ms),
            )
            .where(Call.first_response_latency_ms.is_not(None))
        )
    ).one()
    latency_sample_size = (
        await db.execute(
            base_query()
            .with_only_columns(func.count(Call.id))
            .where(Call.first_response_latency_ms.is_not(None))
        )
    ).scalar_one()

    return CallAnalyticsResponse(
        total_calls=total,
        by_direction={direction.value: count for direction, count in direction_counts},
        by_status={status.value: count for status, count in status_counts},
        by_outcome={outcome: count for outcome, count in outcome_counts},
        duration_seconds_p50=duration_p50,
        duration_seconds_p95=duration_p95,
        first_response_latency_ms_p50=latency_p50,
        first_response_latency_ms_p95=latency_p95,
        first_response_latency_sample_size=latency_sample_size,
    )
