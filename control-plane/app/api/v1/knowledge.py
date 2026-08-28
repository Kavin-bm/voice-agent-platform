import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.queue import get_arq_pool
from app.core.security import get_current_tenant_id
from app.core.storage import put_object
from app.models.business import Business
from app.models.knowledge import Document, KnowledgeSource
from app.schemas.knowledge import (
    DocumentRead,
    DocumentUrlCreate,
    KnowledgeSourceCreate,
    KnowledgeSourceRead,
)

router = APIRouter(tags=["knowledge"])
settings = get_settings()

EXTENSION_TO_SOURCE_TYPE = {"pdf": "pdf", "docx": "docx", "xlsx": "xlsx", "txt": "txt"}


async def _get_owned_knowledge_source(
    knowledge_source_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> KnowledgeSource:
    source = await db.get(KnowledgeSource, knowledge_source_id)
    if source is None or source.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")
    return source


async def _enqueue_ingestion(document: Document) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job("ingest_document", str(document.id))


@router.post(
    "/knowledge-sources", response_model=KnowledgeSourceRead, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_source(
    body: KnowledgeSourceCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeSourceRead:
    business = await db.get(Business, body.business_id)
    if business is None or business.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    source = KnowledgeSource(tenant_id=tenant_id, business_id=body.business_id, name=body.name)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/knowledge-sources", response_model=list[KnowledgeSourceRead])
async def list_knowledge_sources(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[KnowledgeSourceRead]:
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.tenant_id == tenant_id))
    return list(result.scalars().all())


@router.post(
    "/knowledge-sources/{knowledge_source_id}/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    knowledge_source_id: uuid.UUID,
    file: UploadFile,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRead:
    source = await _get_owned_knowledge_source(knowledge_source_id, tenant_id, db)

    extension = (file.filename or "").rsplit(".", 1)[-1].lower()
    source_type = EXTENSION_TO_SOURCE_TYPE.get(extension)
    if source_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type .{extension} — expected pdf/docx/xlsx/txt",
        )

    data = await file.read()
    document = Document(
        tenant_id=tenant_id,
        knowledge_source_id=source.id,
        source_type=source_type,
        source_uri="",
    )
    db.add(document)
    await db.flush()

    object_key = f"{tenant_id}/{document.id}/{file.filename}"
    put_object(settings.minio_documents_bucket, object_key, data, file.content_type or "application/octet-stream")
    document.source_uri = object_key
    await db.commit()
    await db.refresh(document)

    await _enqueue_ingestion(document)
    return document


@router.post(
    "/knowledge-sources/{knowledge_source_id}/documents/url",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_document_from_url(
    knowledge_source_id: uuid.UUID,
    body: DocumentUrlCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRead:
    source = await _get_owned_knowledge_source(knowledge_source_id, tenant_id, db)

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(body.url)
        response.raise_for_status()

    document = Document(
        tenant_id=tenant_id, knowledge_source_id=source.id, source_type="url", source_uri=""
    )
    db.add(document)
    await db.flush()

    object_key = f"{tenant_id}/{document.id}/source.html"
    put_object(settings.minio_documents_bucket, object_key, response.content, "text/html")
    document.source_uri = object_key
    await db.commit()
    await db.refresh(document)

    await _enqueue_ingestion(document)
    return document


@router.get("/knowledge-sources/{knowledge_source_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    knowledge_source_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentRead]:
    await _get_owned_knowledge_source(knowledge_source_id, tenant_id, db)
    result = await db.execute(
        select(Document).where(Document.knowledge_source_id == knowledge_source_id)
    )
    return list(result.scalars().all())


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRead:
    document = await db.get(Document, document_id)
    if document is None or document.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
