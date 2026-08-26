import uuid

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.core.storage import get_object
from app.models.knowledge import Chunk, Document, DocumentStatus
from app.services.ingestion.chunker import chunk_text
from app.services.ingestion.embedder import embed_chunks
from app.services.ingestion.parsers import parse

settings = get_settings()


async def ingest_document(ctx, document_id: str) -> None:
    async with async_session_factory() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        if document is None:
            return

        document.status = DocumentStatus.processing
        await db.commit()

        try:
            data = get_object(settings.minio_documents_bucket, document.source_uri)
            text = parse(document.source_type, data)
            texts = chunk_text(text)
            if not texts:
                raise ValueError("No extractable text in document")

            embeddings = await embed_chunks(db, document.tenant_id, texts)
            for index, (content, embedding) in enumerate(zip(texts, embeddings)):
                db.add(
                    Chunk(
                        tenant_id=document.tenant_id,
                        document_id=document.id,
                        chunk_index=index,
                        content=content,
                        embedding=embedding,
                    )
                )
            document.status = DocumentStatus.ready
            document.error = None
        except Exception as exc:  # noqa: BLE001 - persisted as document.error for the operator
            document.status = DocumentStatus.failed
            document.error = str(exc)

        await db.commit()
