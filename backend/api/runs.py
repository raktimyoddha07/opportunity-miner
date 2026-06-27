"""
Runs API.

Routes (AGENTS.md):
    POST   /runs/start        — start a pipeline run
    GET    /runs              — list runs
    GET    /runs/{id}         — run detail
    DELETE /runs/{id}         — delete a run (+ cascade)

Runs are executed on a background thread so the API responds immediately with
the run row (status="running"). The LangGraph pipeline never aborts on a single
node failure (every node catches + stores errors in state.error), so a run ends
as "completed" even when some stages log non-fatal errors; only an unrecoverable
top-level error marks it "failed".
"""
import threading
import traceback
import uuid as uuidlib
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.connection import SessionLocal, get_db
from backend.db.models import Run
from backend.dependencies import resolve_llm_config
from backend.pipeline.graph import app as pipeline_app
from backend.services.trend_detection import snapshot_run_trends

router = APIRouter(prefix="/runs", tags=["runs"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    subreddits: list[str] = Field(..., min_length=1)
    llm_config: dict | None = None


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def serialize_run(run: Run) -> dict:
    return {
        "id": str(run.id),
        "status": run.status,
        "subreddits": run.subreddits or [],
        "llm_config": run.llm_config or {},
        "error": run.error,
        "created_at": _iso(run.created_at),
        "updated_at": _iso(run.updated_at),
    }


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

def _execute_run(run_id: str, subreddits: list[str], llm_config: dict) -> None:
    """
    Run the full pipeline for a run_id in a background thread.

    Pipeline nodes own their own DB sessions. Here we only update the Run row
    status and capture any top-level failure (node-level errors are already
    captured in state.error and persisted where relevant).
    """
    db = SessionLocal()
    try:
        state = {
            "run_id": run_id,
            "subreddits": subreddits,
            "llm_config": llm_config,
            "status": "running",
            "error": "",
        }
        final_state = pipeline_app.invoke(state)

        error = final_state.get("error") or ""

        # Capture trend snapshots for the dashboard (best-effort, never fatal)
        try:
            snapshot_run_trends(db, run_id)
        except Exception as snap_err:
            print(f"Trend snapshot failed for run {run_id}: {snap_err}")

        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            # No clusters produced AND an error recorded => failed; else completed.
            run.status = "failed" if (not final_state.get("clusters") and error) else "completed"
            if error:
                run.error = error
            run.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        traceback.print_exc()
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.error = f"{type(e).__name__}: {e}"
                run.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/start")
def start_run(
    payload: StartRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    llm_config: dict = Depends(resolve_llm_config),
):
    """Start a new pipeline run for the given subreddits."""
    effective_llm_config = payload.llm_config or llm_config

    run = Run(
        id=str(uuidlib.uuid4()),
        status="running",
        subreddits=payload.subreddits,
        llm_config=effective_llm_config,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_id = str(run.id)
    subs = list(payload.subreddits)
    cfg = dict(effective_llm_config)

    # Offload the heavy pipeline to a daemon thread so the request returns fast.
    thread = threading.Thread(
        target=_execute_run, args=(run_id, subs, cfg), daemon=True
    )
    thread.start()

    return serialize_run(run)


@router.get("")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    return [serialize_run(r) for r in runs]


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return serialize_run(run)


@router.delete("/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(run)  # cascades to all child tables
    db.commit()
    return {"deleted": run_id}
