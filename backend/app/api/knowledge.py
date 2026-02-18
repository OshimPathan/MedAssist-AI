"""
MedAssist AI - Knowledge Base API
Upload, manage, and search hospital knowledge for RAG-enhanced responses
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from typing import Optional, List

from app.models.schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
from app.utils.security import require_role
from app.database.connection import get_db
from app.ai_engine.rag_engine import vector_store, KnowledgeChunk
from app.utils.audit_logger import log_action

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=KnowledgeBaseResponse, status_code=201)
async def add_knowledge(
    kb: KnowledgeBaseCreate,
    user: dict = Depends(require_role("ADMIN")),
):
    """Add a knowledge base entry and index it in the vector store"""
    db = get_db()

    # Save to database
    entry = await db.knowledgebase.create(data={
        "title": kb.title,
        "content": kb.content,
        "category": kb.category,
    })

    # Index in FAISS
    try:
        vector_store.add_documents([
            KnowledgeChunk(
                id=entry.id,
                title=entry.title,
                content=entry.content,
                category=entry.category,
            )
        ])
    except Exception as e:
        logger.error(f"Failed to index in vector store: {e}")

    await log_action("ADD_KNOWLEDGE", "knowledge_base", user["user_id"], {"title": kb.title})

    return KnowledgeBaseResponse(
        id=entry.id, title=entry.title, content=entry.content,
        category=entry.category, is_active=entry.isActive,
        created_at=entry.createdAt,
    )


@router.get("/", response_model=List[KnowledgeBaseResponse])
async def list_knowledge(
    category: Optional[str] = Query(None),
    user: dict = Depends(require_role("ADMIN")),
):
    """List all knowledge base entries"""
    db = get_db()
    filters = {"isActive": True}
    if category:
        filters["category"] = category

    entries = await db.knowledgebase.find_many(
        where=filters,
        order={"createdAt": "desc"},
    )
    return [
        KnowledgeBaseResponse(
            id=e.id, title=e.title, content=e.content,
            category=e.category, is_active=e.isActive,
            created_at=e.createdAt,
        ) for e in entries
    ]


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=2, description="Search query"),
    category: Optional[str] = Query(None),
    top_k: int = Query(5, ge=1, le=20),
):
    """Search knowledge base using semantic similarity (RAG)"""
    results = vector_store.search(query=q, top_k=top_k, category=category)
    return {
        "query": q,
        "results": results,
        "total": len(results),
    }


@router.post("/bulk")
async def bulk_import_knowledge(
    entries: List[KnowledgeBaseCreate],
    user: dict = Depends(require_role("ADMIN")),
):
    """Bulk import knowledge base entries"""
    db = get_db()
    created = []
    chunks = []

    for kb in entries:
        entry = await db.knowledgebase.create(data={
            "title": kb.title,
            "content": kb.content,
            "category": kb.category,
        })
        created.append(entry.id)
        chunks.append(KnowledgeChunk(
            id=entry.id,
            title=entry.title,
            content=entry.content,
            category=entry.category,
        ))

    # Batch index
    try:
        vector_store.add_documents(chunks)
    except Exception as e:
        logger.error(f"Bulk indexing failed: {e}")

    await log_action("BULK_IMPORT_KNOWLEDGE", "knowledge_base", user["user_id"],
                     {"count": len(created)})

    return {"created": len(created), "ids": created}


@router.post("/reindex")
async def reindex_knowledge_base(
    user: dict = Depends(require_role("ADMIN")),
):
    """Rebuild the entire FAISS index from database"""
    db = get_db()
    entries = await db.knowledgebase.find_many(where={"isActive": True})

    vector_store.clear()

    chunks = [
        KnowledgeChunk(id=e.id, title=e.title, content=e.content, category=e.category)
        for e in entries
    ]

    if chunks:
        vector_store.add_documents(chunks)

    await log_action("REINDEX_KNOWLEDGE", "knowledge_base", user["user_id"],
                     {"total": len(chunks)})

    return {"reindexed": len(chunks)}


@router.delete("/{entry_id}")
async def delete_knowledge(
    entry_id: str,
    user: dict = Depends(require_role("ADMIN")),
):
    """Soft-delete a knowledge base entry"""
    db = get_db()
    entry = await db.knowledgebase.find_unique(where={"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")

    await db.knowledgebase.update(
        where={"id": entry_id},
        data={"isActive": False},
    )
    await log_action("DELETE_KNOWLEDGE", "knowledge_base", user["user_id"],
                     {"entry_id": entry_id})
    return {"message": "Entry deleted. Run /reindex to update search index."}


@router.get("/stats")
async def knowledge_stats(
    user: dict = Depends(require_role("ADMIN")),
):
    """Get knowledge base statistics"""
    db = get_db()
    total = await db.knowledgebase.count(where={"isActive": True})
    return {
        "total_entries": total,
        "indexed_documents": vector_store.total_documents,
        "categories": await _get_categories(db),
    }


async def _get_categories(db):
    """Get unique categories with counts"""
    entries = await db.knowledgebase.find_many(
        where={"isActive": True},
    )
    cats = {}
    for e in entries:
        cats[e.category] = cats.get(e.category, 0) + 1
    return cats
