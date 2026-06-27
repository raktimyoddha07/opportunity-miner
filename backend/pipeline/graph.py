"""
LangGraph pipeline definition.

Full flow (see AGENTS.md):

    collect -> clean -> extract -> deduplicate -> cluster -> score -> validate -> generate -> END

Every node honors a strict input/output key contract. The chain of evidence
(Opportunity -> Cluster -> Pain Point -> Source Document + URL) is preserved
end-to-end. No node may abort the whole run; errors are caught and stored in
PipelineState.error.
"""
from langgraph.graph import StateGraph, END

from backend.pipeline.state import PipelineState
from backend.pipeline.nodes.collect import collect_node
from backend.pipeline.nodes.clean import clean_node
from backend.pipeline.nodes.extract import extract_node
from backend.pipeline.nodes.deduplicate import deduplicate_node
from backend.pipeline.nodes.cluster import cluster_node
from backend.pipeline.nodes.score import score_node
from backend.pipeline.nodes.validate import validate_node
from backend.pipeline.nodes.generate import generate_node


def build_pipeline():
    """Construct and compile the full pipeline graph. Returns the runnable app."""
    workflow = StateGraph(PipelineState)

    # 1. Register every node
    workflow.add_node("collect", collect_node)
    workflow.add_node("clean", clean_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("deduplicate", deduplicate_node)
    workflow.add_node("cluster", cluster_node)
    workflow.add_node("score", score_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("generate", generate_node)

    # 2. Linear flow
    workflow.set_entry_point("collect")
    workflow.add_edge("collect", "clean")
    workflow.add_edge("clean", "extract")
    workflow.add_edge("extract", "deduplicate")
    workflow.add_edge("deduplicate", "cluster")
    workflow.add_edge("cluster", "score")
    workflow.add_edge("score", "validate")
    workflow.add_edge("validate", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Compiled app, importable by API/services.
app = build_pipeline()
