"""
LangGraph pipeline state definition.

This TypedDict is the single shared state object threaded through every node
in the pipeline graph:

    collect → clean → extract → deduplicate → cluster → score → validate → generate → END

Architecture rules (see AGENTS.md) that shape this state:
  * Each node reads ONLY its contracted input key and writes ONLY its
    contracted output key. Never reach into another node's output.
  * The chain of evidence must always stay intact:
        Opportunity → Cluster → Pain Point → Original Reddit Comment + URL
  * `error` holds any non-fatal node error so a single failure never aborts
    the whole run (every node must catch, log, and continue).
"""
from typing import TypedDict


class PipelineState(TypedDict):
    # --- Run identity & configuration ---
    run_id: str
    subreddits: list[str]
    llm_config: dict

    # --- Pipeline stage outputs (one per node contract) ---
    source_documents: list[dict]           # collect node output
    cleaned_documents: list[dict]          # clean node output
    pain_points: list[dict]                # extract node output
    deduplicated_pain_points: list[dict]   # deduplicate node output
    clusters: list[dict]                   # cluster node output
    scored_clusters: list[dict]            # score node output
    validated_clusters: list[dict]         # validate node output
    opportunities: list[dict]              # generate node output
    ideas: list[dict]                      # generate node output

    # --- Run lifecycle ---
    status: str                            # "running" | "completed" | "failed"
    error: str                             # last non-fatal error message, if any
