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

def get_extract_prompt_template() -> str:
    """
    Loads extract.txt prompt template from the backend LLM configuration structure.
    """
    dir_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    prompt_path = os.path.join(dir_path, "llm", "prompts", "extract.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def parse_json_from_llm(output_text: str) -> dict:
    """
    Strips markdown JSON wrappers and parses string to dict.
    """
    cleaned = output_text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)

def extract_single_pain_point(llm, content: str, prompt_template: str) -> dict:
    """
    Invokes the LLM to analyze content and parse results, retrying up to 3 times on failures.
    """
    prompt_text = prompt_template.format(content=content)
    for attempt in range(1, 4):
        try:
            response = llm.invoke(prompt_text)
            response_content = response.content if hasattr(response, 'content') else str(response)
            parsed = parse_json_from_llm(response_content)
            
            # Extract attributes
            has_pain_point = parsed.get("has_pain_point", False)
            summary = parsed.get("summary", "")
            category = parsed.get("category", "")
            intensity = parsed.get("intensity", 1)
            quoted_evidence = parsed.get("quoted_evidence", "")
            confidence = parsed.get("confidence", 0)

            # Enforce validation schemas
            if category not in VALID_CATEGORIES:
                category = "manual_work"

            return {
                "has_pain_point": bool(has_pain_point),
                "summary": str(summary),
                "category": str(category),
                "intensity": int(intensity),
                "quoted_evidence": str(quoted_evidence),
                "confidence": int(confidence)
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

    if not cleaned_docs:
        return {"pain_points": []}

    try:
        llm = build_llm(llm_config)
        prompt_template = get_extract_prompt_template()
    except Exception as e:
        error_msg = f"Failed to initialize LLM factory or prompt layout: {str(e)}"
        print(error_msg)
        return {"pain_points": [], "error": error_msg}

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
                    "intensity": db_pain_point.intensity,
                    "quoted_evidence": db_pain_point.quoted_evidence,
                    "confidence": db_pain_point.confidence
                }
                pain_points.append(serialized_pp)
            except Exception as e:
                # Catch error, log it, and continue (Rule 5)
                print(f"Error extracting pain point for doc {doc_id}: {e}")
                # We do not abort the node run; we proceed with other documents.

        db.commit()
        return {"pain_points": pain_points}
    except Exception as e:
        db.rollback()
        error_msg = f"Database commit error in extract node: {str(e)}"
        print(error_msg)
        return {"pain_points": pain_points, "error": error_msg}
    finally:
        db.close()
