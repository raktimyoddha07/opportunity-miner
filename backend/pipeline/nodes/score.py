"""
Score pipeline node.

Contract (see AGENTS.md Node Contracts):
  Input  key: clusters
  Output key: scored_clusters
  Uses LLM: No

Scoring model (see AGENTS.md "Scoring Model"):
  Opportunity Score = Frequency * Intensity * Diversity * Persistence, normalized 0-100.

  Frequency  = cluster mentions / total mentions across all clusters
  Intensity  = average intensity rating (1-5) across the cluster's pain points
  Diversity  = number of unique subreddits mentioning the cluster
  Persistence= whether the problem appears across multiple time periods
               (here: fraction of distinct calendar days spanned by the evidence)

The node reads cluster + evidence data from the DB to compute these signals,
writes the four sub-scores and the final normalized score back onto each
cluster row, and returns the serialized scored clusters.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.connection import SessionLocal
from backend.db.models import Cluster, PainPoint, SourceDocument
from backend.pipeline.state import PipelineState


def _gather_evidence(db: Session, cluster: Cluster):
    """
    Pull the pain points + their original source documents for a cluster.
    Returns (pain_points, source_documents, total_mentions_across_all_clusters).
    """
    pain_points = cluster.pain_points or []
    pp_ids = [p.id for p in pain_points]
    source_docs = []
    if pp_ids:
        source_docs = (
            db.query(SourceDocument)
            .join(PainPoint, PainPoint.source_document_id == SourceDocument.id)
            .filter(PainPoint.id.in_(pp_ids))
            .all()
        )
    return pain_points, source_docs


def compute_frequency(cluster_mentions: int, total_mentions: int) -> float:
    if total_mentions <= 0:
        return 0.0
    return min(cluster_mentions / float(total_mentions), 1.0)


def compute_intensity(pain_points: list) -> float:
    intensities = [p.intensity for p in pain_points if p.intensity is not None]
    if not intensities:
        return 0.0
    avg = sum(intensities) / len(intensities)
    return min(max(avg / 5.0, 0.0), 1.0)  # normalize 1-5 -> 0-1


def compute_diversity(source_docs: list) -> float:
    subreddits = set()
    for doc in source_docs:
        meta = doc.raw_metadata or {}
        sub = meta.get("subreddit")
        if sub:
            subreddits.add(sub)
    # Normalize against a soft cap so 1 subreddit isn't 100%.
    # 5+ unique subreddits saturates the diversity signal.
    return min(len(subreddits) / 5.0, 1.0)


def compute_persistence(source_docs: list) -> float:
    """
    Fraction of distinct calendar days spanned by the evidence, capped.
    3+ distinct days saturates the persistence signal.
    """
    days = set()
    for doc in source_docs:
        if isinstance(doc.created_at, datetime):
            days.add(doc.created_at.date())
    return min(len(days) / 3.0, 1.0)


def score_clusters(clusters: list[dict], run_id, db: Session) -> list[dict]:
    if not clusters:
        return []

    cluster_ids = [c["id"] for c in clusters if c.get("id")]
    cluster_rows = {str(c.id): c for c in db.query(Cluster).filter(Cluster.id.in_(cluster_ids)).all()}

    # Total mentions across all clusters in this run (denominator for frequency)
    total_mentions = (
        db.query(PainPoint).join(Cluster, Cluster.run_id == run_id).count()
        if run_id else 0
    )

    scored: list[dict] = []
    for cd in clusters:
        cluster = cluster_rows.get(cd["id"])
        if not cluster:
            continue

        pain_points = cluster.pain_points or []
        pp_ids = [p.id for p in pain_points]
        source_docs = (
            db.query(SourceDocument)
            .join(PainPoint, PainPoint.source_document_id == SourceDocument.id)
            .filter(PainPoint.id.in_(pp_ids))
            .all()
        ) if pp_ids else []

        mentions = len(pain_points)
        frequency = compute_frequency(mentions, total_mentions)
        intensity = compute_intensity(pain_points)
        diversity = compute_diversity(source_docs)
        persistence = compute_persistence(source_docs)

        persistence_floored = max(persistence, 0.1)
        score = round((
            frequency            * 0.35 +
            intensity            * 0.30 +
            diversity            * 0.25 +
            persistence_floored  * 0.10
        ) * 100.0, 2)

        # Persist back onto the cluster row
        cluster.frequency = round(frequency, 4)
        cluster.intensity = round(intensity, 4)
        cluster.diversity = len({(d.raw_metadata or {}).get("subreddit") for d in source_docs
                                 if (d.raw_metadata or {}).get("subreddit")})
        cluster.persistence = round(persistence, 4)
        cluster.score = score

        scored.append({
            **cd,
            "score": score,
            "frequency": cluster.frequency,
            "intensity": cluster.intensity,
            "diversity": cluster.diversity,
            "persistence": cluster.persistence,
        })

    db.commit()
    return scored


def score_node(state: PipelineState) -> dict:
    """
    Compute the opportunity score for each cluster and persist the sub-signals.
    Input:  clusters, run_id
    Output: scored_clusters
    """
    clusters = state.get("clusters", [])
    run_id = state.get("run_id")
    stats = state.get("pipeline_stats") or {}
    pain_points = state.get("pain_points", [])

    # Minimum Corpus Guard
    if len(pain_points) < 10:
        collect_cnt = len(state.get("source_documents", []))
        clean_cnt = len(state.get("cleaned_documents", []))
        extract_cnt = len(pain_points)
        
        collapse_reason = "collect"
        if collect_cnt >= 10:
            collapse_reason = "clean"
            if clean_cnt >= 10:
                collapse_reason = "extract"
                
        error_msg = (
            f"Insufficient corpus. Run collect on more subreddits before scoring. "
            f"Stage causing collapse: {collapse_reason} (collect={collect_cnt}, clean={clean_cnt}, extract={extract_cnt})"
        )
        print(error_msg)
        stats["score_scored"] = 0
        print("[SCORE]        → 0 scored")
        return {"scored_clusters": [], "error": error_msg, "pipeline_stats": stats}

    if not clusters:
        stats["score_scored"] = 0
        print("[SCORE]        → 0 scored")
        return {"scored_clusters": [], "pipeline_stats": stats}

    db = SessionLocal()
    try:
        scored = score_clusters(clusters, run_id, db)
        stats["score_scored"] = len(scored)
        print(f"[SCORE]        → {len(scored)} scored")
        return {"scored_clusters": scored, "pipeline_stats": stats}
    except Exception as e:
        db.rollback()
        error_msg = f"Score node error: {e}"
        print(error_msg)
        stats["score_scored"] = len(clusters)
        return {"scored_clusters": clusters, "error": error_msg, "pipeline_stats": stats}
    finally:
        db.close()
