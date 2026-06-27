import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Mode
    ENV: str = "development"
    DEBUG: bool = True

    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/reddit_miner"

    # Reddit API Credentials
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "RedditOpportunityMiner/0.1"
    REDDIT_USERNAME: Optional[str] = None
    REDDIT_PASSWORD: Optional[str] = None

    # LLM API Keys / Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Pipeline Settings
    DEFAULT_DEDUPLICATION_THRESHOLD: float = 0.85
    MIN_MENTIONS_THRESHOLD: int = 10
    MIN_USERS_THRESHOLD: int = 3
    MIN_THREADS_THRESHOLD: int = 2
    MIN_CONFIDENCE_SCORE_THRESHOLD: float = 2.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
