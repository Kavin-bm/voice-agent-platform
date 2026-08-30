import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.knowledge import Chunk, Document, DocumentStatus, KnowledgeSource
from app.services.ingestion.embedder import embed_chunks

RESULT_LIMIT = 5


async def search_knowledge(db: AsyncSession, business_id: uuid.UUID, query: str) -> list[str]:
    """Powers the search_knowledge tool Dograh calls mid-call. Scoped to one
    business's ready documents only — never returns content across
    businesses/tenants, and never touches documents still processing or
    that failed."""

    business = await db.get(Business, business_id)
    if business is None:
        return []

    [query_embedding] = await embed_chunks(db, business.tenant_id, [query])

    result = await db.execute(
        select(Chunk.content)
        .join(Document, Chunk.document_id == Document.id)
        .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
        .where(
            KnowledgeSource.business_id == business_id,
            Document.status == DocumentStatus.ready,
        )
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(RESULT_LIMIT)
    )
    return list(result.scalars().all())
