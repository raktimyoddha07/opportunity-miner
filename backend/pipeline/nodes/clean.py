from backend.reddit.filters import should_discard_content
from backend.pipeline.state import PipelineState

def clean_node(state: PipelineState) -> dict:
    """
    Filters raw source documents and drops low-signal content.
    Inputs: source_documents
    Outputs: cleaned_documents
    """
    source_docs = state.get("source_documents", [])
    cleaned_docs = []

    for doc in source_docs:
        content = doc.get("content", "")
        # Filter content
        should_discard, reason = should_discard_content(content)
        if not should_discard:
            cleaned_docs.append(doc)
        else:
            # We can log discarded items for debug/traceability
            print(f"Discarded document {doc.get('source_id')}: {reason}")

    return {"cleaned_documents": cleaned_docs}
