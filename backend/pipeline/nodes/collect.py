from backend.db.connection import SessionLocal
from backend.db.models import SourceDocument, Run
from backend.reddit.collector import collect_from_subreddits
from backend.pipeline.state import PipelineState

def collect_node(state: PipelineState) -> dict:
    """
    Collects raw Reddit posts/comments and saves them to the database before passing downstream.
    Inputs: subreddits, run_id, llm_config
    Outputs: source_documents
    """
    run_id = state.get("run_id")
    subreddits = state.get("subreddits", [])
    
    # 1. Collect from Reddit
    try:
        raw_docs = collect_from_subreddits(subreddits)
    except Exception as e:
        print(f"Collection node error: {e}")
        return {"source_documents": [], "error": f"Collection error: {str(e)}"}

    # 2. Save raw source documents to DB (Rule 6: Never process before saving)
    db = SessionLocal()
    try:
        # Check if Run exists, otherwise create it
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            run = Run(
                id=run_id,
                subreddits=subreddits,
                llm_config=state.get("llm_config", {}),
                status="running"
            )
            db.add(run)
            db.commit()

        db_docs = []
        for doc in raw_docs:
            db_doc = SourceDocument(
                run_id=run_id,
                source=doc["source"],
                source_id=doc["source_id"],
                title=doc["title"],
                content=doc["content"],
                author=doc["author"],
                url=doc["url"],
                created_at=doc["created_at"],
                raw_metadata=doc["metadata"]
            )
            db.add(db_doc)
            db_docs.append(db_doc)
        
        db.commit()

        # Serialize results to pass down to downstream nodes
        serialized_docs = []
        for db_doc in db_docs:
            serialized_docs.append({
                "id": str(db_doc.id),
                "source": db_doc.source,
                "source_id": db_doc.source_id,
                "title": db_doc.title,
                "content": db_doc.content,
                "author": db_doc.author,
                "url": db_doc.url,
                "created_at": db_doc.created_at,
                "metadata": db_doc.raw_metadata
            })
        return {"source_documents": serialized_docs}
    except Exception as e:
        db.rollback()
        print(f"Error persisting source documents in database: {e}")
        return {"source_documents": [], "error": f"Database error during collection: {str(e)}"}
    finally:
        db.close()
