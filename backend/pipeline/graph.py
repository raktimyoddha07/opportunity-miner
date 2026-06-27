"""
LangGraph pipeline definition.

Full flow (see AGENTS.md + extralogic.md):

    collect -> clean -> enrich -> extract -> deduplicate -> cluster -> score -> validate -> generate -> END

  enrich: urgency keyword pre-scorer + spaCy entity extraction (between clean and extract)

Every node honors a strict input/output key contract. The chain of evidence
(Opportunity -> Cluster -> Pain Point -> Source Document + URL) is preserved
end-to-end. No node may abort the whole run; errors are caught and stored in
PipelineState.error.
"""
from langgraph.graph import StateGraph, END

from backend.pipeline.state import PipelineState
from backend.pipeline.nodes.collect import collect_node
from backend.pipeline.nodes.clean import clean_node
from backend.pipeline.nodes.enrich import enrich_node
from backend.pipeline.nodes.extract import extract_node
from backend.pipeline.nodes.deduplicate import deduplicate_node
from backend.pipeline.nodes.cluster import cluster_node
from backend.pipeline.nodes.score import score_node
from backend.pipeline.nodes.validate import validate_node
from backend.pipeline.nodes.generate import generate_node


def check_cancel_wrapper(node_func):
    def wrapper(state):
        run_id = state.get("run_id")
        if run_id:
            from backend.db.connection import SessionLocal
            from backend.db.models import Run
            db = SessionLocal()
            try:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run and (run.status == "failed" or run.error == "Stopped by user"):
                    raise RuntimeError("Stopped by user")
            finally:
                db.close()
        return node_func(state)
    return wrapper


def build_pipeline():
    """Construct and compile the full pipeline graph. Returns the runnable app."""
    workflow = StateGraph(PipelineState)

    # 1. Register every node
    workflow.add_node("collect", check_cancel_wrapper(collect_node))
    workflow.add_node("clean", check_cancel_wrapper(clean_node))
    workflow.add_node("enrich", check_cancel_wrapper(enrich_node))
    workflow.add_node("extract", check_cancel_wrapper(extract_node))
    workflow.add_node("deduplicate", check_cancel_wrapper(deduplicate_node))
    workflow.add_node("cluster", check_cancel_wrapper(cluster_node))
    workflow.add_node("score", check_cancel_wrapper(score_node))
    workflow.add_node("validate", check_cancel_wrapper(validate_node))
    workflow.add_node("generate", check_cancel_wrapper(generate_node))

    # 2. Linear flow (enrich inserted between clean and extract)
    workflow.set_entry_point("collect")
    workflow.add_edge("collect", "clean")
    workflow.add_edge("clean", "enrich")
    workflow.add_edge("enrich", "extract")
    workflow.add_edge("extract", "deduplicate")
    workflow.add_edge("deduplicate", "cluster")
    workflow.add_edge("cluster", "score")
    workflow.add_edge("score", "validate")
    workflow.add_edge("validate", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()



# Compiled app, importable by API/services.
app = build_pipeline()
