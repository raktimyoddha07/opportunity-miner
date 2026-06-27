"""
Validate pipeline node.

Contract (see AGENTS.md Node Contracts):
  Input  key: scored_clusters
  Output key: validated_clusters
  Uses LLM: Yes (1 attempt)

This is the gatekeeper. An opportunity is only valid if it clears BOTH:
  (a) the LLM's judgement (is_valid + confidence), AND
  (b) the hard evidence thresholds from config (Rule 7):
        - >= MIN_MENTIONS_THRESHOLD   unique mentions
        - >= MIN_USERS_THRESHOLD      unique users
        - >= MIN_THREADS_THRESHOLD    unique threads
        - average confidence score    >= MIN_CONFIDENCE_SCORE_THRESHOLD

Rule 7 is non-negotiable: "Bad opportunities are worse than missing ones."
When in doubt, reject — never lower the threshold.

Validated clusters are persisted as Opportunity rows (is_valid reflects the
final decision). Invalid ones are still recorded so the evidence chain and the
rejection reasoning are preserved for later inspection.
"""
import json
import os

from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.connection import SessionLocal
from backend.db.models import Cluster, Opportunity, PainPoint, SourceDocument
from backend.llm.factory import build_llm
from backend.pipeline.state import PipelineState
from backend.services.external_validation import run_external_validation


def _prompt_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "llm", "prompts", "validate.txt"
    )


def parse_json_from_llm(output_text: str) -> dict:
    cleaned = output_text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def build_evidence_text(pain_points: list, source_docs_by_pp: dict) -> str:
    """Compose a compact, quotable evidence block for the LLM."""
    lines = []
    for pp in pain_points[:25]:  # cap to keep prompt bounded
        quote = (pp.quoted_evidence or pp.summary or "").strip()
        doc = source_docs_by_pp.get(str(pp.id))
        sub = ""
        url = ""
        if doc:
            sub = (doc.raw_metadata or {}).get("subreddit", "")
            url = doc.url or ""
        lines.append(f'- "{quote[:280]}"' + (f" — r/{sub}" if sub else "") + (f" ({url})" if url else ""))
    return "\n".join(lines) if lines else "(no quotable evidence collected)"


def gather_cluster_signals(db: Session, cluster: Cluster):
    """Return (pain_points, source_docs_by_pp, unique_users, unique_threads, mentions)."""
    pain_points = cluster.pain_points or []
    pp_ids = [p.id for p in pain_points]
    docs = []
    by_pp = {}
    if pp_ids:
        rows = (
            db.query(PainPoint, SourceDocument)
            .join(SourceDocument, SourceDocument.id == PainPoint.source_document_id)
            .filter(PainPoint.id.in_(pp_ids))
            .all()
        )
        for pp, doc in rows:
            docs.append(doc)
            by_pp[str(pp.id)] = doc

    users = {d.author for d in docs if d.author and d.author != "[deleted]"}
    # "thread" = distinct submission/post. We approximate with the post id
    # embedded in permalink/source metadata; fall back to the document title.
    threads = set()
    for d in docs:
        meta = d.raw_metadata or {}
        parent = meta.get("parent_id") or meta.get("permalink") or d.url
        # parent_id like 't3_abc123' points to the submission; collapse to that
        if isinstance(parent, str) and parent.startswith("t1_"):
            # comment-level parent; use permalink stem instead
            parent = d.url
        threads.add(parent)
    mentions = len(pain_points)
    return pain_points, by_pp, len(users), len(threads), mentions


def meets_thresholds(mentions, users, threads, avg_confidence) -> tuple[bool, str]:
    """Apply Rule 7 hard thresholds. Returns (passes, reason_if_failed)."""
    if mentions < settings.MIN_MENTIONS_THRESHOLD:
        return False, f"mentions {mentions} < {settings.MIN_MENTIONS_THRESHOLD}"
    if users < settings.MIN_USERS_THRESHOLD:
        return False, f"unique users {users} < {settings.MIN_USERS_THRESHOLD}"
    if threads < settings.MIN_THREADS_THRESHOLD:
        return False, f"unique threads {threads} < {settings.MIN_THREADS_THRESHOLD}"
    if avg_confidence < settings.MIN_CONFIDENCE_SCORE_THRESHOLD:
        return False, (f"avg confidence {avg_confidence:.2f} < "
                       f"{settings.MIN_CONFIDENCE_SCORE_THRESHOLD}")
    return True, ""


def validate_single_cluster(llm, cluster_dict: dict, db: Session, run_id) -> dict:
    cluster = db.query(Cluster).filter(Cluster.id == cluster_dict["id"]).first()
    if not cluster:
        return {**cluster_dict, "validated": False}

    pain_points, by_pp, users, threads, mentions = gather_cluster_signals(db, cluster)

    # Average confidence across member pain points (LLM-extracted 0-100 scale,
    # normalized to 0-5 for the threshold comparison per AGENTS.md spec)
    confidences = [p.confidence for p in pain_points if p.confidence is not None]
    avg_conf_pct = (sum(confidences) / len(confidences)) if confidences else 0.0
    avg_conf_5 = avg_conf_pct / 20.0  # 0-100 -> 0-5

    # 1. Hard evidence thresholds (Rule 7) — checked first and never bypassed
    threshold_pass, fail_reason = meets_thresholds(mentions, users, threads, avg_conf_5)

    # 2. LLM judgement (1 attempt)
    is_valid = False
    llm_confidence = int(avg_conf_pct)
    reasoning = ""
    try:
        with open(_prompt_path(), "r", encoding="utf-8") as f:
            template = f.read()
        evidence = build_evidence_text(pain_points, by_pp)
        prompt = template.format(problem=cluster.summary, evidence=evidence)
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        parsed = parse_json_from_llm(text)
        is_valid = bool(parsed.get("is_valid", False))
        llm_confidence = int(parsed.get("confidence", avg_conf_pct))
        reasoning = str(parsed.get("reasoning", ""))
    except Exception as e:
        reasoning = f"LLM validation unavailable ({e}); relied on thresholds only."

    # Final decision = LLM AND thresholds (reject when in doubt)
    final_valid = bool(is_valid and threshold_pass)
    if not threshold_pass:
        reasoning = (reasoning + f" | Threshold check failed: {fail_reason}.").strip(" |")

    # --- External validation (Upgrade 5) — only run for opportunities that pass ---
    external_signals: dict = {}
    if final_valid:
        try:
            external_signals = run_external_validation(
                topic=cluster.name,
                internal_confidence=llm_confidence,
            )
        except Exception as ext_e:
            print(f"[validate] External validation failed for '{cluster.name}': {ext_e}")

    external_confidence = external_signals.get("external_confidence", llm_confidence)

    opportunity = Opportunity(
        cluster_id=cluster.id,
        title=cluster.name,
        summary=cluster.summary,
        category=cluster.category,
        score=cluster.score,
        confidence=external_confidence if final_valid else llm_confidence,
        reasoning=reasoning,
        is_valid=final_valid,
        external_signals=external_signals,
    )
    db.add(opportunity)
    db.flush()

    return {
        **cluster_dict,
        "opportunity_id": str(opportunity.id),
        "is_valid": final_valid,
        "confidence": opportunity.confidence,
        "reasoning": reasoning,
        "mentions": mentions,
        "unique_users": users,
        "unique_threads": threads,
        "external_signals": external_signals,
    }


def validate_node(state: PipelineState) -> dict:
    """
    Validate scored clusters into opportunities.
    Input:  scored_clusters, run_id, llm_config
    Output: validated_clusters
    """
    scored = state.get("scored_clusters", [])
    run_id = state.get("run_id")
    llm_config = state.get("llm_config", {})

    if not scored:
        return {"validated_clusters": []}

    try:
        llm = build_llm(llm_config)
    except Exception as e:
        error_msg = f"Validate node could not build LLM: {e}"
        print(error_msg)
        return {"validated_clusters": [], "error": error_msg}

    db = SessionLocal()
    validated: list[dict] = []
    try:
        for cd in scored:
            try:
                validated.append(validate_single_cluster(llm, cd, db, run_id))
            except Exception as e:
                print(f"Validation failed for cluster {cd.get('id')}: {e}")
                validated.append({**cd, "is_valid": False,
                                  "reasoning": f"validation error: {e}"})
        db.commit()
        return {"validated_clusters": validated}
    except Exception as e:
        db.rollback()
        error_msg = f"Validate node persistence error: {e}"
        print(error_msg)
        return {"validated_clusters": validated, "error": error_msg}
    finally:
        db.close()
