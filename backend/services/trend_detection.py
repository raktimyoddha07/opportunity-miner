"""
Trend detection service.

Backs the per-run `trend_snapshots` table and the dashboard trend graph. The
core idea (AGENTS.md "Scoring Model" → Persistence): a problem that recurs
across multiple runs / time periods is a stronger signal than a one-off spike.

This service:
  - captures a frequency snapshot for every cluster in a run (so trends can be
    compared across runs later),
  - reconstructs a time series of cluster frequencies across runs for the
    dashboard.

Source-agnostic: operates purely on ORM rows + pain point dicts.
"""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.db.models import Cluster, Run, TrendSnapshot


def snapshot_run_trends(db: Session, run_id: str) -> list[TrendSnapshot]:
    """
    Persist one TrendSnapshot per cluster for the given run.

    `frequency` here is the cluster's normalized frequency signal (0-1) already
    computed by the `score` node — the right grain for cross-run comparison.

    Idempotent: re-running for the same run replaces no rows (caller controls
    run lifecycle), but we avoid double-inserting by deleting prior snapshots
    for the run first.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return []

    # Clear any prior snapshots for this run (e.g. re-run scenario)
    db.query(TrendSnapshot).filter(TrendSnapshot.run_id == run_id).delete()

    clusters = db.query(Cluster).filter(Cluster.run_id == run_id).all()
    now = datetime.now(timezone.utc)
    snapshots: list[TrendSnapshot] = []
    for cluster in clusters:
        snap = TrendSnapshot(
            run_id=run_id,
            cluster_name=cluster.name,
            frequency=float(cluster.frequency or 0.0),
            snapshot_date=now,
        )
        db.add(snap)
        snapshots.append(snap)

    db.flush()
    return snapshots


def build_trend_series(db: Session, cluster_name: str | None = None) -> list[dict]:
    """
    Reconstruct a time series of cluster frequencies across all runs, ordered
    chronologically. Used by the dashboard trend graph.

    Returns a list of:
      { run_id, cluster_name, frequency, snapshot_date }
    Optionally filtered to a single cluster_name.
    """
    q = db.query(TrendSnapshot, Run).join(Run, Run.id == TrendSnapshot.run_id)
    if cluster_name:
        q = q.filter(TrendSnapshot.cluster_name == cluster_name)
    q = q.order_by(Run.created_at.asc(), TrendSnapshot.cluster_name.asc())

    out: list[dict] = []
    for snap, run in q.all():
        out.append({
            "id": str(snap.id),
            "run_id": str(snap.run_id),
            "cluster_name": snap.cluster_name,
            "frequency": float(snap.frequency or 0.0),
            "snapshot_date": snap.snapshot_date.isoformat() if snap.snapshot_date else None,
            "run_created_at": run.created_at.isoformat() if run.created_at else None,
        })
    return out


def detect_emerging_clusters(db: Session, top_n: int = 10) -> list[dict]:
    """
    Heuristic "emerging" signal: clusters whose latest-run frequency exceeds
    their historical average frequency across prior runs.

    Returns the top_n strongest emerging clusters:
      { cluster_name, latest_frequency, prior_avg, delta }
    """
    series = build_trend_series(db)
    by_cluster: dict[str, list[dict]] = defaultdict(list)
    for row in series:
        by_cluster[row["cluster_name"]].append(row)

    emerging: list[dict] = []
    for name, points in by_cluster.items():
        if len(points) < 2:
            # Not enough history to call a trend; surface current strength only.
            latest = points[-1]["frequency"] if points else 0.0
            emerging.append({
                "cluster_name": name,
                "latest_frequency": latest,
                "prior_avg": 0.0,
                "delta": latest,
            })
            continue
        latest = points[-1]["frequency"]
        prior = [p["frequency"] for p in points[:-1]]
        prior_avg = sum(prior) / len(prior) if prior else 0.0
        emerging.append({
            "cluster_name": name,
            "latest_frequency": latest,
            "prior_avg": prior_avg,
            "delta": latest - prior_avg,
        })

    emerging.sort(key=lambda x: x["delta"], reverse=True)
    return emerging[:top_n]
