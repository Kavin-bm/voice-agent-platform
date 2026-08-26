import uuid

import litellm
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import ProviderType
from app.services.credentials import get_credential

# Fixed for MVP: Chunk.embedding is a fixed-width pgvector column
# (EMBEDDING_DIM=1536 in app/models/knowledge.py), so the embedding model
# can't vary per tenant the way the conversational LLM/voice can — that
# would need per-tenant vector columns or a re-embed migration. Tenants pick
# their own conversational LLM (e.g. Gemini Flash for latency) but need an
# OpenAI credential specifically for embeddings until this is made
# pluggable, which isn't worth building without a second embedding
# model actually in use.
EMBEDDING_MODEL = "text-embedding-3-small"


async def embed_chunks(db: AsyncSession, tenant_id: uuid.UUID, texts: list[str]) -> list[list[float]]:
    credential = await get_credential(db, tenant_id, ProviderType.llm, "openai")
    if credential is None or not credential.get("api_key"):
        raise ValueError(
            "No OpenAI credential configured for this tenant — required for knowledge-base "
            "embeddings even if the conversational LLM is a different provider."
        )

    response = await litellm.aembedding(
        model=EMBEDDING_MODEL, input=texts, api_key=credential["api_key"]
    )
    return [item["embedding"] for item in response.data]
