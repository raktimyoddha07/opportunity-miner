"""
Settings API.

Routes (AGENTS.md):
    GET  /settings   — current settings (active LLMConfig + pipeline controls)
    POST /settings   — upsert the active LLMConfig (+ optional subreddits store)

The LLMConfig row is the persisted provider/model configuration. Only one row
may be active at a time; saving a new active config deactivates the previous one
so the rest of the system has a single source of truth (factory.py / runs).
Validation thresholds live in config.py and are surfaced read-only here.
"""
import uuid as uuidlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.connection import get_db
from backend.db.models import LLMConfig
from backend.dependencies import get_app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMConfigPayload(BaseModel):
    provider: str
    model: str
    config: dict = {}
    is_active: bool = True


class SettingsPayload(BaseModel):
    llm_config: LLMConfigPayload
    subreddits: list[str] = []
    pipeline: dict | None = None  # accepted but not persisted (thresholds are config-driven)


@router.get("")
def get_settings(settings: dict = Depends(get_app_settings)):
    return settings


@router.post("")
def save_settings(
    payload: SettingsPayload,
    db: Session = Depends(get_db),
):
    """Persist the active LLM config. Deactivates any previously active row."""
    cfg_in = payload.llm_config

    # Deactivate prior active configs
    db.query(LLMConfig).filter(LLMConfig.is_active.is_(True)).update(
        {LLMConfig.is_active: False}, synchronize_session=False
    )

    config = LLMConfig(
        id=str(uuidlib.uuid4()),
        provider=cfg_in.provider,
        model=cfg_in.model,
        config=cfg_in.config or {},
        is_active=cfg_in.is_active,
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    return {
        "llm_config": {
            "id": str(config.id),
            "provider": config.provider,
            "model": config.model,
            "config": config.config,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat() if config.created_at else None,
        },
        "subreddits": payload.subreddits,
        "note": (
            "Pipeline thresholds are config-driven (config.py); they are not "
            "persisted from this endpoint."
        ),
    }
