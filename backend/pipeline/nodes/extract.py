import os
import json
from backend.config import settings
from backend.llm.factory import build_llm
from backend.db.connection import SessionLocal
from backend.db.models import PainPoint
from backend.pipeline.state import PipelineState

# Categories constraint list
VALID_CATEGORIES = {
    "manual_work", "missing_software", "bad_software", "workflow_bottleneck",
    "reporting", "compliance", "data_entry", "automation", "communication",
    "scheduling", "integration_gap", "expensive_service"
}

VALID_EMOTIONS = {
    "frustrated_with_workaround", "paying_for_bad_tool", "asking_for_missing_feature",
    "abandoned_by_vendor", "time_wasted", "data_loss_fear", "onboarding_confusion",
    "integration_broken"
}

def get_extract_prompt_template() -> str:
    """
    Loads extract.txt prompt template from the backend LLM configuration structure.
    """
    dir_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    prompt_path = os.path.join(dir_path, "llm", "prompts", "extract.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

from backend.llm.parser import parse_json_from_llm

def extract_single_pain_point(llm, content: str, prompt_template: str) -> dict:
    """
    Invokes the LLM to analyze content and parse results, retrying up to 3 times on failures.
    """
    prompt_text = prompt_template.replace("{content}", content)
    for attempt in range(1, 4):
        try:
            response = llm.invoke(prompt_text)
            response_content = response.content if hasattr(response, 'content') else str(response)
            parsed = parse_json_from_llm(response_content)
            
            # Extract attributes safely handling None or missing keys
            has_pain_point = parsed.get("has_pain_point", False)
            summary = parsed.get("summary", "") or ""
            category = parsed.get("category", "") or ""
            emotion = parsed.get("emotion", "") or ""
            quoted_evidence = parsed.get("quoted_evidence", "") or ""

            raw_intensity = parsed.get("intensity")
            try:
                intensity = int(raw_intensity) if raw_intensity is not None else 1
            except (ValueError, TypeError):
                intensity = 1

            raw_confidence = parsed.get("confidence")
            try:
                confidence = int(raw_confidence) if raw_confidence is not None else 0
            except (ValueError, TypeError):
                confidence = 0

            # Enforce validation schemas
            if category not in VALID_CATEGORIES:
                category = "manual_work"
            if emotion not in VALID_EMOTIONS:
                emotion = ""

            return {
                "has_pain_point": bool(has_pain_point),
                "summary": str(summary),
                "category": str(category),
                "emotion": str(emotion),
                "intensity": intensity,
                "quoted_evidence": str(quoted_evidence),
                "confidence": confidence
            }
        except Exception as e:
            print(f"Extraction attempt {attempt} failed: {e}")
            if attempt == 3:
                raise e

def extract_node(state: PipelineState) -> dict:
    """
    Extracts pain points from cleaned documents using the LLM factory.
    Inputs: cleaned_documents, run_id, llm_config
    Outputs: pain_points
    """
    run_id = state.get("run_id")
    cleaned_docs = state.get("cleaned_documents", [])
    llm_config = state.get("llm_config", {})
    stats = state.get("pipeline_stats") or {}

    if not cleaned_docs:
        stats["extract_true"] = 0
        stats["extract_false"] = 0
        print("[EXTRACT]      → 0 has_pain_point=true, 0 false")
        return {"pain_points": [], "pipeline_stats": stats}

    try:
        llm = build_llm(llm_config)
        prompt_template = get_extract_prompt_template()
    except Exception as e:
        error_msg = f"Failed to initialize LLM factory or prompt layout: {str(e)}"
        print(error_msg)
        return {"pain_points": [], "error": error_msg, "pipeline_stats": stats}

    pain_points = []
    db = SessionLocal()
    try:
        for doc in cleaned_docs:
            doc_id = doc.get("id")
            content = doc.get("content", "")
            
            try:
                # LLM execution (with max 3 retries)
                result = extract_single_pain_point(llm, content, prompt_template)
                
                # Write to database (Rule 5: never let a single document crash node)
                db_pain_point = PainPoint(
                    run_id=run_id,
                    source_document_id=doc_id,
                    has_pain_point=result["has_pain_point"],
                    summary=result["summary"],
                    category=result["category"],
                    emotion=result["emotion"],
                    intensity=result["intensity"],
                    quoted_evidence=result["quoted_evidence"],
                    confidence=result["confidence"]
                )
                db.add(db_pain_point)
                db.flush()

                serialized_pp = {
                    "id": str(db_pain_point.id),
                    "source_document_id": doc_id,
                    "has_pain_point": db_pain_point.has_pain_point,
                    "summary": db_pain_point.summary,
                    "category": db_pain_point.category,
                    "emotion": db_pain_point.emotion,
                    "intensity": db_pain_point.intensity,
                    "quoted_evidence": db_pain_point.quoted_evidence,
                    "confidence": db_pain_point.confidence
                }
                pain_points.append(serialized_pp)
            except Exception as e:
                # Catch error, log it, and continue (Rule 5)
                print(f"Error extracting pain point for doc {doc_id}: {e}")
                
                # Fallback: Check if urgency_score >= 3
                metadata = doc.get("metadata") or {}
                urgency_score = metadata.get("urgency_score", 0)
                if urgency_score >= 3:
                    print(f"Applying fallback confidence scoring for doc {doc_id} because urgency_score={urgency_score}")
                    try:
                        db_pain_point = PainPoint(
                            run_id=run_id,
                            source_document_id=doc_id,
                            has_pain_point=True,
                            summary=doc.get("title") or doc.get("content")[:100],
                            category="manual_work",
                            intensity=3,
                            quoted_evidence="Fallback due to LLM error. Urgency score: " + str(urgency_score),
                            confidence=30
                        )
                        db.add(db_pain_point)
                        db.flush()

                        serialized_pp = {
                            "id": str(db_pain_point.id),
                            "source_document_id": doc_id,
                            "has_pain_point": db_pain_point.has_pain_point,
                            "summary": db_pain_point.summary,
                            "category": db_pain_point.category,
                            "intensity": db_pain_point.intensity,
                            "quoted_evidence": db_pain_point.quoted_evidence,
                            "confidence": db_pain_point.confidence,
                            "source": "urgency_fallback"
                        }
                        pain_points.append(serialized_pp)
                    except Exception as fallback_e:
                        print(f"Fallback failed for doc {doc_id}: {fallback_e}")

        db.commit()
        
        extract_true = sum(1 for p in pain_points if p.get("has_pain_point"))
        extract_false = len(pain_points) - extract_true
        stats["extract_true"] = extract_true
        stats["extract_false"] = extract_false
        print(f"[EXTRACT]      → {extract_true} has_pain_point=true, {extract_false} false")

        return {"pain_points": pain_points, "pipeline_stats": stats}
    except Exception as e:
        db.rollback()
        error_msg = f"Database commit error in extract node: {str(e)}"
        print(error_msg)
        return {"pain_points": pain_points, "error": error_msg, "pipeline_stats": stats}
    finally:
        db.close()
