"""
Exports + Trends API.

Export routes (AGENTS.md):
    GET /export/csv       — CSV report (Opportunity Report)
    GET /export/json      — full nested JSON
    GET /export/markdown  — Markdown report

Trend routes (dashboard trend graph):
    GET /trends           — frequency time series across runs
    GET /trends/emerging  — top emerging clusters (latest vs prior avg)

The export dataset is assembled by services/exports.gather_export_dataset and
rendered by the pure serializers in backend/exports/*.py.
"""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.exports.csv_export import export_csv
from backend.exports.json_export import export_json
from backend.exports.markdown_export import export_markdown
from backend.services.exports import gather_export_dataset
from backend.services.trend_detection import build_trend_series, detect_emerging_clusters

router = APIRouter(tags=["exports", "trends"])


@router.get("/export/csv")
def export_csv_route(db: Session = Depends(get_db)):
    dataset = gather_export_dataset(db, only_valid=True)
    return Response(
        content=export_csv(dataset),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=opportunities.csv"},
    )


@router.get("/export/json")
def export_json_route(db: Session = Depends(get_db)):
    dataset = gather_export_dataset(db, only_valid=True)
    return Response(
        content=export_json(dataset),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=opportunities.json"},
    )


@router.get("/export/markdown")
def export_markdown_route(db: Session = Depends(get_db)):
    dataset = gather_export_dataset(db, only_valid=True)
    return Response(
        content=export_markdown(dataset),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=opportunities.md"},
    )


@router.get("/trends")
def trends_route(
    db: Session = Depends(get_db),
    cluster_name: str | None = Query(None),
):
    """Frequency time series of clusters across runs (for the trend graph)."""
    return build_trend_series(db, cluster_name=cluster_name)


@router.get("/trends/emerging")
def emerging_route(db: Session = Depends(get_db)):
    """Top emerging clusters (latest-run frequency vs historical average)."""
    return detect_emerging_clusters(db)
