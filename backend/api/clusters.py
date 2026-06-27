"""
Clusters API.

Routes (AGENTS.md):
    GET /clusters             — list (filters: run_id, category, min_score)
    GET /clusters/{id}        — detail with member pain points (evidence)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.db.models import Cluster

router = APIRouter(prefix="/clusters", tags=["clusters"])


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def serialize_cluster(cluster: Cluster, include_pain_points: bool = False) -> dict:
    payload = {
        "id": str(cluster.id),
        "run_id": str(cluster.run_id),
        "name": cluster.name,
        "summary": cluster.summary,
        "category": cluster.category,
        "score": cluster.score,
        "frequency": cluster.frequency,
        "intensity": cluster.intensity,
        "diversity": cluster.diversity,
        "persistence": cluster.persistence,
        "duplicate_count": cluster.duplicate_count,
        "duplicate_ids": cluster.duplicate_ids or [],
        "created_at": _iso(cluster.created_at),
    }
    if include_pain_points:
        payload["pain_points"] = [
            {
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
            for pp in (cluster.pain_points or [])
        ]
    return payload


@router.get("")
def list_clusters(
    db: Session = Depends(get_db),
    run_id: str | None = Query(None),
    category: str | None = Query(None),
    min_score: float | None = Query(None, ge=0, le=100),
):
    q = db.query(Cluster)
    if run_id:
        q = q.filter(Cluster.run_id == run_id)
    if category:
        q = q.filter(Cluster.category == category)
    if min_score is not None:
        q = q.filter(Cluster.score >= min_score)
    q = q.order_by(Cluster.score.desc())
    return [serialize_cluster(c) for c in q.all()]


@router.get("/{cluster_id}")
def get_cluster(cluster_id: str, db: Session = Depends(get_db)):
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return serialize_cluster(cluster, include_pain_points=True)
