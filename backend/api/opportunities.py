"""
Opportunities API.

Routes (AGENTS.md):
    GET /opportunities        — ranked list (filters: category, run_id, min_score, valid_only)
    GET /opportunities/{id}   — detail with cluster + nested ideas + evidence

An opportunity is a validated cluster. The evidence chain
(Opportunity -> Cluster -> Pain Point -> Source Document) is always preserved
and surfaced on the detail endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.db.models import Cluster, Idea, Opportunity

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def serialize_opportunity(opp: Opportunity, include_nested: bool = False) -> dict:
    payload = {
        "id": str(opp.id),
        "cluster_id": str(opp.cluster_id),
        "title": opp.title,
        "summary": opp.summary,
        "category": opp.category,
        "score": opp.score,
        "confidence": opp.confidence,
        "reasoning": opp.reasoning,
        "is_valid": opp.is_valid,
        "external_signals": getattr(opp, "external_signals", {}) or {},
        "created_at": _iso(opp.created_at),
    }
    if include_nested:
        cluster = opp.cluster
        payload["cluster"] = {
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
            "created_at": _iso(cluster.created_at),
        } if cluster else None
        payload["ideas"] = [
            {
                "id": str(i.id),
                "opportunity_id": str(i.opportunity_id),
                "type": i.type,
                "title": i.title,
                "description": i.description,
                "created_at": _iso(i.created_at),
            }
            for i in (opp.ideas or [])
        ]
    return payload


@router.get("")
def list_opportunities(
    db: Session = Depends(get_db),
    category: str | None = Query(None, description="Filter by pain-point category"),
    run_id: str | None = Query(None, description="Filter by run id"),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum score"),
    valid_only: bool | None = Query(None, description="Only validated opportunities"),
):
    q = db.query(Opportunity)
    if category:
        q = q.filter(Opportunity.category == category)
    if run_id:
        q = q.join(Cluster, Cluster.id == Opportunity.cluster_id).filter(Cluster.run_id == run_id)
    if min_score is not None:
        q = q.filter(Opportunity.score >= min_score)
    if valid_only:
        q = q.filter(Opportunity.is_valid.is_(True))

    q = q.order_by(Opportunity.score.desc())
    return [serialize_opportunity(o) for o in q.all()]


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return serialize_opportunity(opp, include_nested=True)
