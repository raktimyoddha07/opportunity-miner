"""
Settings API.

Routes (AGENTS.md):
    GET  /settings   — current settings (active LLMConfig + pipeline controls)
    POST /settings   — upsert the active LLMConfig + subreddits + pipeline controls

The LLMConfig row is the persisted provider/model configuration. Only one row
may be active at a time; saving a new active config deactivates the previous one
so the rest of the system has a single source of truth (factory.py / runs).
Subreddits and pipeline controls are persisted in PipelineSettings.
"""
import uuid as uuidlib

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.db.models import LLMConfig, PipelineSettings
from backend.config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMConfigPayload(BaseModel):
    provider: str
    model: str
    config: dict = {}
    is_active: bool = True


class PipelinePayload(BaseModel):
    feeds: list[str] = ["hot", "top", "rising", "new"]
    feed_limit: int = 100
    comment_depth: int = 3
    dedup_threshold: float = 0.85
    min_length: int = 40
    validation: dict = {}


class SettingsPayload(BaseModel):
    llm_config: LLMConfigPayload
    subreddits: list[str] = []
    pipeline: PipelinePayload | None = None


def _get_active_llm(db: Session):
    return (
        db.query(LLMConfig)
        .filter(LLMConfig.is_active.is_(True))
        .order_by(LLMConfig.created_at.desc())
        .first()
    )


def _get_active_pipeline(db: Session):
    return (
        db.query(PipelineSettings)
        .filter(PipelineSettings.is_active.is_(True))
        .order_by(PipelineSettings.updated_at.desc())
        .first()
    )


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    active_llm = _get_active_llm(db)
    active_pipeline = _get_active_pipeline(db)

    llm_config = {
        "id": str(active_llm.id) if active_llm else None,
        "provider": active_llm.provider if active_llm else "ollama",
        "model": active_llm.model if active_llm else "qwen2.5:7b-instruct",
        "config": active_llm.config if active_llm else {"base_url": "http://localhost:11434"},
        "is_active": True,
        "created_at": active_llm.created_at.isoformat() if active_llm and active_llm.created_at else None,
    }

    subreddits = active_pipeline.subreddits if active_pipeline else []

    return {
        "llm_config": llm_config,
        "subreddits": subreddits,
        "pipeline": {
            "feeds": active_pipeline.feeds if active_pipeline else ["hot", "top", "rising", "new"],
            "feed_limit": active_pipeline.feed_limit if active_pipeline else 100,
            "comment_depth": active_pipeline.comment_depth if active_pipeline else 3,
            "dedup_threshold": active_pipeline.dedup_threshold if active_pipeline else app_settings.DEFAULT_DEDUPLICATION_THRESHOLD,
            "min_length": active_pipeline.min_length if active_pipeline else 40,
            "validation": {
                "min_unique_mentions": app_settings.MIN_MENTIONS_THRESHOLD,
                "min_unique_users": app_settings.MIN_USERS_THRESHOLD,
                "min_unique_threads": app_settings.MIN_THREADS_THRESHOLD,
                "min_avg_confidence": app_settings.MIN_CONFIDENCE_SCORE_THRESHOLD,
            },
        },
    }


@router.post("")
def save_settings(
    payload: SettingsPayload,
    db: Session = Depends(get_db),
):
    """Persist the active LLM config, subreddits, and pipeline controls."""
    cfg_in = payload.llm_config

    # Upsert LLM config — deactivate old active row first
    db.query(LLMConfig).filter(LLMConfig.is_active.is_(True)).update(
        {LLMConfig.is_active: False}, synchronize_session=False
    )
    config = LLMConfig(
        id=str(uuidlib.uuid4()),
        provider=cfg_in.provider,
        model=cfg_in.model,
        config=cfg_in.config or {},
        is_active=True,
    )
    db.add(config)

    # Upsert PipelineSettings — deactivate old row and create new active one
    db.query(PipelineSettings).filter(PipelineSettings.is_active.is_(True)).update(
        {PipelineSettings.is_active: False}, synchronize_session=False
    )
    pipeline_in = payload.pipeline
    ps = PipelineSettings(
        id=str(uuidlib.uuid4()),
        subreddits=payload.subreddits,
        feeds=pipeline_in.feeds if pipeline_in else ["hot", "top", "rising", "new"],
        feed_limit=pipeline_in.feed_limit if pipeline_in else 100,
        comment_depth=pipeline_in.comment_depth if pipeline_in else 3,
        dedup_threshold=pipeline_in.dedup_threshold if pipeline_in else 0.85,
        min_length=pipeline_in.min_length if pipeline_in else 40,
        is_active=True,
    )
    db.add(ps)

    db.commit()
    db.refresh(config)
    db.refresh(ps)

    return {
        "llm_config": {
            "id": str(config.id),
            "provider": config.provider,
            "model": config.model,
            "config": config.config,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat() if config.created_at else None,
        },
        "subreddits": ps.subreddits,
        "pipeline": {
            "feeds": ps.feeds,
            "feed_limit": ps.feed_limit,
            "comment_depth": ps.comment_depth,
            "dedup_threshold": ps.dedup_threshold,
            "min_length": ps.min_length,
            "validation": {
                "min_unique_mentions": app_settings.MIN_MENTIONS_THRESHOLD,
                "min_unique_users": app_settings.MIN_USERS_THRESHOLD,
                "min_unique_threads": app_settings.MIN_THREADS_THRESHOLD,
                "min_avg_confidence": app_settings.MIN_CONFIDENCE_SCORE_THRESHOLD,
            },
        },
    }
