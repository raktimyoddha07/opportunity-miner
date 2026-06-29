"""
Cluster pipeline node.

Contract (see AGENTS.md Node Contracts):
  Input  key: deduplicated_pain_points
  Output key: clusters
  Uses LLM: No

Strategy:
  - Group deduplicated pain points by their `category`.
  - Within a category, run a simple text-similarity pass (normalized term overlap)
    so unrelated complaints in the same category do not get jammed together.
  - For every resulting group, build a Cluster row with a representative name
    (derived from the strongest summary) and link all member pain points via
    the cluster_evidence association table.

Source-agnostic: relies only on the standard pain point dict fields
(category, summary, id, source_document_id). No Reddit-specific logic.
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.db.connection import SessionLocal
from backend.db.models import Cluster, PainPoint, cluster_evidence
from backend.pipeline.state import PipelineState


def _tokenize(text: str) -> set[str]:
    return {tok for tok in (text or "").lower().split() if len(tok) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _similarity_group_key(summary: str, threshold: float = 0.34) -> str:
    """
    Produce a coarse sub-group key for summaries in the same category.
    Two summaries with enough shared vocabulary land in the same sub-group.
    Implemented as a stable hash of the sorted token set for simplicity and
    determinism; richer clustering lives in services/clustering.py.
    """
    tokens = sorted(_tokenize(summary))
    # Bucket by the leading tokens so similar summaries collide
    head = tuple(tokens[:6]) if tokens else ()
    import hashlib
    return hashlib.md5(repr(head).encode("utf-8")).hexdigest()


def cluster_pain_points(pain_points: list[dict]) -> list[dict]:
    """
    Pure grouping step — no DB. Returns cluster dicts ready for persistence:
      { name, summary, category, pain_point_ids: [uuid, ...] }
    """
    by_category: dict[str, list[dict]] = defaultdict(list)
    for pp in pain_points:
        category = pp.get("category") or "uncategorized"
        by_category[category].append(pp)

    clusters: list[dict] = []
    for category, members in by_category.items():
        # Sub-group within a category using term overlap
        sub_groups: list[list[dict]] = []
        for pp in members:
            placed = False
            for group in sub_groups:
                rep = group[0]
                if _jaccard(_tokenize(pp.get("summary", "")),
                            _tokenize(rep.get("summary", ""))) >= 0.34:
                    group.append(pp)
                    placed = True
                    break
            if not placed:
                sub_groups.append([pp])

        for group in sub_groups:
            # Pick the highest-confidence member as the representative summary
            rep = max(group, key=lambda p: (p.get("confidence") or 0, p.get("intensity") or 0))
            summary = rep.get("summary") or rep.get("quoted_evidence") or category
            name = _derive_name(category, summary)
            clusters.append({
                "name": name,
                "summary": summary,
                "category": category,
                "pain_point_ids": [p.get("id") for p in group if p.get("id")],
            })

    return clusters


def _derive_name(category: str, summary: str) -> str:
    words = (summary or "").strip().split()
    short = " ".join(words[:8]).strip().rstrip(".,;")
    return short.capitalize() if short else category.replace("_", " ").title()


def cluster_node(state: PipelineState) -> dict:
    """
    Group deduplicated pain points into clusters and persist them (with evidence
    links) to the database.
    Input:  deduplicated_pain_points, run_id
    Output: clusters
    """
    run_id = state.get("run_id")
    pain_points = state.get("deduplicated_pain_points", [])

    if not pain_points:
        return {"clusters": []}

    try:
        cluster_dicts = cluster_pain_points(pain_points)
    except Exception as e:
        error_msg = f"Cluster grouping error: {e}"
        print(error_msg)
        return {"clusters": [], "error": error_msg}

    db: Session = SessionLocal()
    serialized: list[dict] = []
    try:
        # Map of pain_point_id -> ORM PainPoint for evidence linking
        pp_ids = {pp_id for c in cluster_dicts for pp_id in c["pain_point_ids"]}
        pain_point_map = {}
        if pp_ids:
            rows = db.query(PainPoint).filter(PainPoint.id.in_(list(pp_ids))).all()
            pain_point_map = {str(p.id): p for p in rows}

        for cd in cluster_dicts:
            cluster = Cluster(
                run_id=run_id,
                name=cd["name"],
                summary=cd["summary"],
                category=cd["category"],
            )
            # Link evidence pain points before flush so association populates
            linked = [pain_point_map[pid] for pid in cd["pain_point_ids"]
                      if pid in pain_point_map]
            cluster.pain_points = linked

            # Roll duplicate counts up onto the cluster for scoring convenience
            cluster.duplicate_count = sum(
                p.duplicate_count if hasattr(p, "duplicate_count") else 1
                for p in linked
            )
            db.add(cluster)
            db.flush()

            serialized.append({
                "id": str(cluster.id),
                "run_id": str(run_id),
                "name": cluster.name,
                "summary": cluster.summary,
                "category": cluster.category,
                "score": cluster.score,
                "frequency": cluster.frequency,
                "intensity": cluster.intensity,
                "diversity": cluster.diversity,
                "persistence": cluster.persistence,
                "duplicate_count": cluster.duplicate_count,
                "duplicate_ids": [],
                "pain_point_ids": [str(p.id) for p in linked],
            })

        db.commit()
        return {"clusters": serialized}
    except Exception as e:
        db.rollback()
        error_msg = f"Cluster persistence error: {e}"
        print(error_msg)
        return {"clusters": serialized, "error": error_msg}
    finally:
        db.close()
