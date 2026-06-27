import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Mode
    ENV: str = "development"
    DEBUG: bool = True

    # Database Settings
    DATABASE_URL: Optional[str] = None

    # Reddit API Credentials
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "RedditOpportunityMiner/0.1"

    # LLM API Keys / Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = None

    # Pipeline Settings
    DEFAULT_DEDUPLICATION_THRESHOLD: float = 0.82
    MIN_MENTIONS_THRESHOLD: int = 3      # lowered from 10: single-subreddit runs are smaller
    MIN_USERS_THRESHOLD: int = 2         # lowered from 3
    MIN_THREADS_THRESHOLD: int = 1       # lowered from 2
    MIN_CONFIDENCE_SCORE_THRESHOLD: float = 1.5  # lowered from 2.0

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
