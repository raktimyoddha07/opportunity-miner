"""
Ideas API.

Routes (AGENTS.md):
    GET  /ideas                — list ideas (filters: opportunity_id, type)
    GET  /ideas/{id}           — idea detail
    POST /ideas/generate       — regenerate ideas for a validated opportunity

Architecture rule: "Do not generate ideas directly from raw posts — only from
validated opportunities." So /ideas/generate refuses to run for opportunities
with is_valid=False.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.db.models import Cluster, Idea, Opportunity, PainPoint, SourceDocument
from backend.dependencies import resolve_llm_config
from backend.llm.factory import build_llm
from backend.pipeline.nodes.generate import (
    VALID_IDEA_TYPES,
    parse_json_from_llm,
)

router = APIRouter(tags=["ideas"])


def _prompt_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "llm", "prompts", "generate.txt"
    )


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def serialize_idea(idea: Idea) -> dict:
    return {
        "id": str(idea.id),
        "opportunity_id": str(idea.opportunity_id),
        "type": idea.type,
        "title": idea.title,
        "description": idea.description,
        "created_at": _iso(idea.created_at),
    }


class GenerateIdeasRequest(BaseModel):
    opportunity_id: str


def _build_evidence_text(db: Session, cluster: Cluster) -> str:
    pp_ids = [p.id for p in (cluster.pain_points or [])]
    if not pp_ids:
        return cluster.summary or "(no evidence)"
    rows = (
        db.query(PainPoint, SourceDocument)
        .join(SourceDocument, SourceDocument.id == PainPoint.source_document_id)
        .filter(PainPoint.id.in_(pp_ids))
        .all()
    )
    lines = []
    for pp, doc in rows[:20]:
        quote = (pp.quoted_evidence or pp.summary or "").strip()[:280]
        sub = (doc.raw_metadata or {}).get("subreddit", "") if doc else ""
        lines.append(f'- "{quote}"' + (f" — r/{sub}" if sub else ""))
    return "\n".join(lines) if lines else cluster.summary


@router.get("/ideas")
def list_ideas(
    db: Session = Depends(get_db),
    opportunity_id: str | None = Query(None),
    type: str | None = Query(None, description="Filter by idea type"),
):
    q = db.query(Idea)
    if opportunity_id:
        q = q.filter(Idea.opportunity_id == opportunity_id)
    if type:
        q = q.filter(Idea.type == type)
    q = q.order_by(Idea.created_at.desc())
    return [serialize_idea(i) for i in q.all()]


@router.get("/ideas/{idea_id}")
def get_idea(idea_id: str, db: Session = Depends(get_db)):
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return serialize_idea(idea)


@router.post("/ideas/generate")
def generate_ideas(
    payload: GenerateIdeasRequest,
    db: Session = Depends(get_db),
    llm_config: dict = Depends(resolve_llm_config),
):
    """
    Regenerate ideas for a validated opportunity.

    Refuses non-validated opportunities (Rule: only generate from validated ops).
    Any error during LLM generation surfaces as 502 with a clear message rather
    than silently returning nothing.
    """
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.id == payload.opportunity_id)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not opportunity.is_valid:
        raise HTTPException(
            status_code=400,
            detail="Ideas can only be generated for validated opportunities.",
        )

    cluster = (
        db.query(Cluster).filter(Cluster.id == opportunity.cluster_id).first()
    )
    if not cluster:
        raise HTTPException(status_code=404, detail="Backing cluster not found")

    try:
        llm = build_llm(llm_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM unavailable: {e}")

    try:
        with open(_prompt_path(), "r", encoding="utf-8") as f:
            template = f.read()
        evidence = _build_evidence_text(db, cluster)
        prompt = template.format(evidence=evidence, problem=cluster.summary)
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        parsed = parse_json_from_llm(text)
        ideas_map = parsed.get("ideas", parsed) if isinstance(parsed, dict) else {}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Idea generation failed: {e}")

    # Replace prior ideas for this opportunity so regeneration is idempotent-ish.
    db.query(Idea).filter(Idea.opportunity_id == opportunity.id).delete()

    created: list[dict] = []
    for idea_type in VALID_IDEA_TYPES:
        entry = ideas_map.get(idea_type) if isinstance(ideas_map, dict) else None
        if not entry:
            continue
        if isinstance(entry, str):
            parts = entry.strip().split("\n", 1)
            title, description = (parts + [parts[0]])[:2] if len(parts) == 1 else parts
        else:
            title = str(entry.get("title", idea_type))
            description = str(entry.get("description", ""))

        idea = Idea(
            opportunity_id=opportunity.id,
            type=idea_type,
            title=title[:255],
            description=description,
        )
        db.add(idea)
        db.flush()
        created.append(serialize_idea(idea))

    db.commit()
    return created
