"""
Evidence API — the trust layer.

Routes (AGENTS.md + frontend contract):
    GET /evidence                 — pain points (+ joined source documents)
    GET /evidence?cluster_id=...  — pain points for a single cluster
    GET /evidence/{cluster_id}    — same, path-param form
    GET /evidence/sources         — raw source documents

The chain of evidence (Pain Point -> Source Document + URL) is always intact.
This is what makes every opportunity auditable back to the original post/comment.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.db.models import Cluster, PainPoint, SourceDocument

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def serialize_source_document(doc: SourceDocument) -> dict:
    return {
        "id": str(doc.id),
        "run_id": str(doc.run_id),
        "source": doc.source,
        "source_id": doc.source_id,
        "title": doc.title,
        "content": doc.content,
        "author": doc.author,
        "url": doc.url,
        "created_at": _iso(doc.created_at),
        "metadata": doc.raw_metadata or {},
        "collected_at": _iso(doc.collected_at),
    }


def serialize_pain_point(pp: PainPoint, doc: SourceDocument | None = None) -> dict:
    payload = {
        "id": str(pp.id),
        "run_id": str(pp.run_id),
        "source_document_id": str(pp.source_document_id),
        "has_pain_point": pp.has_pain_point,
        "summary": pp.summary,
        "category": pp.category,
        "intensity": pp.intensity,
        "quoted_evidence": pp.quoted_evidence,
        "confidence": pp.confidence,
        "created_at": _iso(pp.created_at),
    }
    if doc is not None:
        payload["source_document"] = serialize_source_document(doc)
    return payload


@router.get("/sources")
def list_source_documents(
    db: Session = Depends(get_db),
    run_id: str | None = Query(None),
):
    """Raw source documents — the never-discarded source of truth."""
    q = db.query(SourceDocument)
    if run_id:
        q = q.filter(SourceDocument.run_id == run_id)
    q = q.order_by(SourceDocument.collected_at.desc())
    return [serialize_source_document(d) for d in q.all()]


def _get_evidence(db: Session, cluster_id: str | None, run_id: str | None) -> list[dict]:
    pain_point_ids: list | None = None
    if cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        pain_point_ids = [pp.id for pp in (cluster.pain_points or [])]

    q = (
        db.query(PainPoint, SourceDocument)
        .join(SourceDocument, SourceDocument.id == PainPoint.source_document_id)
    )
    if pain_point_ids is not None:
        q = q.filter(PainPoint.id.in_(pain_point_ids))
    if run_id:
        q = q.filter(PainPoint.run_id == run_id)

    q = q.order_by(PainPoint.confidence.desc().nullslast(), PainPoint.created_at.desc())
    return [serialize_pain_point(pp, doc) for pp, doc in q.all()]


@router.get("")
def list_evidence(
    db: Session = Depends(get_db),
    cluster_id: str | None = Query(None),
    run_id: str | None = Query(None),
):
    """
    Pain points with their joined source documents.
    Optionally scoped to a single cluster (via query param).
    """
    return _get_evidence(db, cluster_id, run_id)


@router.get("/{cluster_id}")
def get_cluster_evidence(
    cluster_id: str,
    db: Session = Depends(get_db),
    run_id: str | None = Query(None),
):
    """
    Pain points with their joined source documents.
    Optionally scoped to a single cluster (via path param).
    """
    return _get_evidence(db, cluster_id, run_id)
