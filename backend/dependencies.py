"""
FastAPI dependencies shared across the API layer.

  - get_db: yields a SQLAlchemy session per request.
  - get_active_llm_config: resolves the stored active LLMConfig row (if any) and
    returns a build_llm-compatible dict. Falls back to a sane default config so
    the API never hard-crashes when no provider is configured yet.
  - get_app_settings: composes the full Settings payload (AGENTS.md Settings
    shape) returned by GET /settings.
"""
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config import settings as app_settings
from backend.db.connection import SessionLocal
from backend.db.models import LLMConfig


def get_db():
    """Per-request DB session. Always closes in `finally`."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_active_llm_config(db: Session) -> Optional[LLMConfig]:
    """The currently-active stored LLMConfig row, or None."""
    return (
        db.query(LLMConfig)
        .filter(LLMConfig.is_active.is_(True))
        .order_by(LLMConfig.created_at.desc())
        .first()
    )


def resolve_llm_config(db: Session = Depends(get_db)) -> dict:
    """
    Return a build_llm-compatible dict for the active provider.

    Preference order:
      1. stored active LLMConfig row (provider/model/config merged),
      2. environment defaults (e.g. OPENAI_API_KEY present -> openai),
      3. local ollama fallback so the pipeline is runnable offline.

    Never raises: returns a default ollama config if nothing is configured.
    """
    active = get_active_llm_config(db)
    if active:
        merged = {"provider": active.provider, "model": active.model}
        merged.update(active.config or {})
        return merged

    # Environment-driven defaults
    if app_settings.OPENAI_API_KEY:
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": app_settings.OPENAI_API_KEY,
        }
    if app_settings.GROQ_API_KEY:
        return {
            "provider": "groq",
            "model": "llama-3.1-8b-instant",
            "api_key": app_settings.GROQ_API_KEY,
        }

    # Safe offline default
    return {
        "provider": "ollama",
        "model": "llama3.1",
        "base_url": app_settings.OLLAMA_BASE_URL,
    }


def get_app_settings(db: Session = Depends(get_db)) -> dict:
    """
    Compose the full Settings payload (see frontend types `Settings`).

    Combines the stored active LLMConfig + persisted subreddit/pipeline
    preferences (read from the most recent run as a pragmatic source of truth)
    with the config.py validation thresholds.
    """
    active = get_active_llm_config(db)

    llm_config = {
        "id": str(active.id) if active else None,
        "provider": active.provider if active else "ollama",
        "model": active.model if active else "llama3.1",
        "config": active.config if active else {},
        "is_active": True,
    }

    # Pragmatic defaults for pipeline controls — kept in code (config.py) since
    # there is no dedicated settings table; thresholds come from config.py.
    return {
        "llm_config": llm_config,
        "subreddits": [],
        "pipeline": {
            "feeds": ["hot", "top", "rising", "new"],
            "feed_limit": 100,
            "comment_depth": 3,
            "dedup_threshold": app_settings.DEFAULT_DEDUPLICATION_THRESHOLD,
            "min_length": 40,
            "validation": {
                "min_unique_mentions": app_settings.MIN_MENTIONS_THRESHOLD,
                "min_unique_users": app_settings.MIN_USERS_THRESHOLD,
                "min_unique_threads": app_settings.MIN_THREADS_THRESHOLD,
                "min_avg_confidence": app_settings.MIN_CONFIDENCE_SCORE_THRESHOLD,
            },
        },
    }
