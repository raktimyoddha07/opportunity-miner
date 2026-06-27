"""
Exports service.

Gathers and serializes validated opportunities (+ their full evidence chain)
into the three formats defined in AGENTS.md "Export Formats": CSV, JSON, Markdown.

This service is the single place that assembles the export dataset so the three
format-specific modules (backend/exports/*.py) stay pure serializers with no DB
access. The evidence chain is always preserved:
    Opportunity -> Cluster -> Pain Point -> Source Document (URL)
"""
from sqlalchemy.orm import Session

from backend.db.models import (
    Cluster,
    Idea,
    Opportunity,
    PainPoint,
    SourceDocument,
)


def gather_export_dataset(db: Session, only_valid: bool = True) -> dict:
    """
    Build the nested export dataset used by all three exporters.

    Returns:
      {
        opportunities: [...],   # one row per opportunity, with cluster + ideas
        clusters:      [...],   # one row per cluster, with pain points
        evidence:      [...],   # one row per pain point, with source document
        ideas:         [...],   # flat list of all ideas
      }

    Every row is a JSON-safe dict (UUIDs -> str, datetimes -> isoformat).
    """
    # --- Opportunities (optionally only validated ones) --------------------
    opp_q = db.query(Opportunity)
    if only_valid:
        opp_q = opp_q.filter(Opportunity.is_valid.is_(True))
    opportunities = opp_q.order_by(Opportunity.score.desc()).all()

    opp_ids = [o.id for o in opportunities]
    cluster_ids = {o.cluster_id for o in opportunities}

    # --- Ideas for those opportunities -------------------------------------
    ideas_by_opp: dict[str, list[Idea]] = {}
    if opp_ids:
        for idea in db.query(Idea).filter(Idea.opportunity_id.in_(opp_ids)).all():
            ideas_by_opp.setdefault(str(idea.opportunity_id), []).append(idea)

    # --- Clusters backing the opportunities --------------------------------
    clusters_by_id: dict[str, Cluster] = {}
    if cluster_ids:
        for c in db.query(Cluster).filter(Cluster.id.in_(list(cluster_ids))).all():
            clusters_by_id[str(c.id)] = c

    # --- Pain points + source documents (evidence) for those clusters ------
    pp_ids = set()
    for c in clusters_by_id.values():
        for pp in (c.pain_points or []):
            pp_ids.add(pp.id)

    docs_by_pp: dict[str, SourceDocument] = {}
    if pp_ids:
        rows = (
            db.query(PainPoint, SourceDocument)
            .join(SourceDocument, SourceDocument.id == PainPoint.source_document_id)
            .filter(PainPoint.id.in_(list(pp_ids)))
            .all()
        )
        for pp, doc in rows:
            docs_by_pp[str(pp.id)] = doc

    # --- Serialize ----------------------------------------------------------
    opportunities_out = []
    ideas_out: list[dict] = []
    for o in opportunities:
        opp_ideas = ideas_by_opp.get(str(o.id), [])
        opportunities_out.append(_serialize_opportunity(o, opp_ideas))
        ideas_out.extend(_serialize_idea(i) for i in opp_ideas)

    clusters_out = []
    evidence_out = []
    for cid, cluster in clusters_by_id.items():
        clusters_out.append(_serialize_cluster(cluster))
        for pp in (cluster.pain_points or []):
            evidence_out.append(_serialize_pain_point(pp, docs_by_pp.get(str(pp.id)), cluster_id=cid))

    return {
        "opportunities": opportunities_out,
        "clusters": clusters_out,
        "evidence": evidence_out,
        "ideas": ideas_out,
    }


# ---------------------------------------------------------------------------
# Row serializers (JSON-safe)
# ---------------------------------------------------------------------------

def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _serialize_source_document(doc: SourceDocument) -> dict:
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


def _serialize_pain_point(pp: PainPoint, doc: SourceDocument | None,
                          cluster_id: str | None = None) -> dict:
    return {
        "id": str(pp.id),
        "run_id": str(pp.run_id),
        "cluster_id": cluster_id,
        "source_document_id": str(pp.source_document_id),
        "has_pain_point": pp.has_pain_point,
        "summary": pp.summary,
        "category": pp.category,
        "intensity": pp.intensity,
        "quoted_evidence": pp.quoted_evidence,
        "confidence": pp.confidence,
        "created_at": _iso(pp.created_at),
        "source_document": _serialize_source_document(doc) if doc else None,
    }


def _serialize_cluster(cluster: Cluster) -> dict:
    return {
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


def _serialize_opportunity(opp: Opportunity, ideas: list[Idea]) -> dict:
    return {
        "id": str(opp.id),
        "cluster_id": str(opp.cluster_id),
        "title": opp.title,
        "summary": opp.summary,
        "category": opp.category,
        "score": opp.score,
        "confidence": opp.confidence,
        "reasoning": opp.reasoning,
        "is_valid": opp.is_valid,
        "created_at": _iso(opp.created_at),
        "ideas": [_serialize_idea(i) for i in ideas],
    }


def _serialize_idea(idea: Idea) -> dict:
    return {
        "id": str(idea.id),
        "opportunity_id": str(idea.opportunity_id),
        "type": idea.type,
        "title": idea.title,
        "description": idea.description,
        "created_at": _iso(idea.created_at),
    }
