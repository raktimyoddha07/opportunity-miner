"""
Generate pipeline node.

Contract (see AGENTS.md Node Contracts):
  Input  key: validated_clusters
  Output key: opportunities, ideas
  Uses LLM: Yes (1 attempt per opportunity)

Architecture rule: "Do not generate ideas directly from raw posts — only from
validated opportunities." So this node ONLY generates ideas for clusters that
passed validation (is_valid=True). Invalid clusters are still surfaced as
Opportunity records (so the rejection reasoning + evidence chain is preserved)
but receive no generated ideas.

Each valid opportunity gets ideas across all 8 idea types defined in AGENTS.md.
"""
import json
import os

from sqlalchemy.orm import Session

from backend.db.connection import SessionLocal
from backend.db.models import Cluster, Idea, Opportunity, PainPoint, SourceDocument
from backend.llm.factory import build_llm
from backend.pipeline.state import PipelineState


VALID_IDEA_TYPES = [
    "micro_saas",
    "ai_agent",
    "chrome_extension",
    "api_product",
    "marketplace",
    "service_business",
    "internal_tool",
    "workflow_automation",
]


def _prompt_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "llm", "prompts", "generate.txt"
    )


def parse_json_from_llm(output_text: str) -> dict:
    cleaned = output_text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def build_evidence_text(db: Session, cluster: Cluster) -> str:
    pain_points = cluster.pain_points or []
    pp_ids = [p.id for p in pain_points]
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


def generate_ideas_for_opportunity(llm, db: Session, cluster: Cluster,
                                   opportunity: Opportunity) -> list[dict]:
    """Call the LLM once per opportunity and persist all returned idea types."""
    try:
        with open(_prompt_path(), "r", encoding="utf-8") as f:
            template = f.read()
        evidence = build_evidence_text(db, cluster)
        prompt = template.format(evidence=evidence, problem=cluster.summary)
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        parsed = parse_json_from_llm(text)
        ideas_map = parsed.get("ideas", parsed) if isinstance(parsed, dict) else {}
    except Exception as e:
        print(f"Idea generation LLM call failed for opportunity {opportunity.id}: {e}")
        return []

    serialized: list[dict] = []
    for idea_type in VALID_IDEA_TYPES:
        entry = ideas_map.get(idea_type) if isinstance(ideas_map, dict) else None
        if not entry:
            continue
        if isinstance(entry, str):
            title, description = entry.strip().split("\n", 1) if "\n" in entry else (entry.strip(), entry.strip())
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
        serialized.append({
            "id": str(idea.id),
            "opportunity_id": str(opportunity.id),
            "type": idea_type,
            "title": idea.title,
            "description": idea.description,
        })
    return serialized


def _print_funnel_summary(stats: dict) -> None:
    """Print the full per-stage funnel summary to stdout."""
    print("\n── Pipeline Funnel Summary ─────────────────────────")
    print(f"[COLLECT]      → {stats.get('collect_documents', '?')} documents")
    print(f"[CLEAN]        → {stats.get('clean_kept', '?')} kept, {stats.get('clean_discarded', '?')} discarded")
    print(f"[ENRICH]       → {stats.get('enrich_passed', '?')} passed urgency filter, {stats.get('enrich_skipped', '?')} skipped")
    print(f"[EXTRACT]      → {stats.get('extract_true', '?')} has_pain_point=true, {stats.get('extract_false', '?')} false")
    print(f"[DEDUPLICATE]  → {stats.get('deduplicate_unique', '?')} unique clusters")
    print(f"[SCORE]        → {stats.get('score_scored', '?')} scored")
    print(f"[VALIDATE]     → {stats.get('validate_passed', '?')} passed, {stats.get('validate_rejected', '?')} rejected")
    print(f"[GENERATE]     → {stats.get('generate_ideas', '?')} ideas generated")
    print("────────────────────────────────────────────────────\n")


def generate_node(state: PipelineState) -> dict:
    """
    Generate opportunities + ideas from validated clusters.
    Input:  validated_clusters, run_id, llm_config
    Output: opportunities, ideas
    """
    validated = state.get("validated_clusters", [])
    run_id = state.get("run_id")
    llm_config = state.get("llm_config", {})
    stats = state.get("pipeline_stats") or {}

    if not validated:
        stats["generate_ideas"] = 0
        _print_funnel_summary(stats)
        return {"opportunities": [], "ideas": [], "pipeline_stats": stats}

    try:
        llm = build_llm(llm_config)
    except Exception as e:
        error_msg = f"Generate node could not build LLM: {e}"
        print(error_msg)
        stats["generate_ideas"] = 0
        _print_funnel_summary(stats)
        return {"opportunities": [], "ideas": [], "error": error_msg, "pipeline_stats": stats}

    db = SessionLocal()
    opportunities_out: list[dict] = []
    ideas_out: list[dict] = []
    try:
        # Index opportunities created during the validate node by cluster id
        opp_by_cluster = {
            str(o.cluster_id): o
            for o in db.query(Opportunity)
            .join(Cluster, Cluster.id == Opportunity.cluster_id)
            .filter(Cluster.run_id == run_id)
            .all()
        } if run_id else {}

        for vc in validated:
            cluster_id = vc.get("id")
            opportunity = opp_by_cluster.get(cluster_id)
            cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first() if cluster_id else None

            if not opportunity or not cluster:
                continue

            opp_serialized = {
                "id": str(opportunity.id),
                "cluster_id": cluster_id,
                "title": opportunity.title,
                "summary": opportunity.summary,
                "category": opportunity.category,
                "score": opportunity.score,
                "confidence": opportunity.confidence,
                "is_valid": opportunity.is_valid,
                "reasoning": opportunity.reasoning,
            }
            opportunities_out.append(opp_serialized)

            # Only generate ideas for genuinely validated opportunities (Rule)
            if not opportunity.is_valid:
                continue

            try:
                ideas = generate_ideas_for_opportunity(llm, db, cluster, opportunity)
                ideas_out.extend(ideas)
            except Exception as e:
                print(f"Idea generation failed for opportunity {opportunity.id}: {e}")

        db.commit()
        stats["generate_ideas"] = len(ideas_out)
        print(f"[GENERATE]     → {len(ideas_out)} ideas generated")
        _print_funnel_summary(stats)
        return {"opportunities": opportunities_out, "ideas": ideas_out, "pipeline_stats": stats}
    except Exception as e:
        db.rollback()
        error_msg = f"Generate node persistence error: {e}"
        print(error_msg)
        stats["generate_ideas"] = len(ideas_out)
        _print_funnel_summary(stats)
        return {"opportunities": opportunities_out, "ideas": ideas_out, "error": error_msg, "pipeline_stats": stats}
    finally:
        db.close()
