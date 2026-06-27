import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.db.connection import Base

# Association table for Cluster <-> PainPoint evidence (Many-to-Many)
cluster_evidence = Table(
    "cluster_evidence",
    Base.metadata,
    Column("cluster_id", UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True),
    Column("pain_point_id", UUID(as_uuid=True), ForeignKey("pain_points.id", ondelete="CASCADE"), primary_key=True)
)

class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed
    subreddits = Column(JSON, nullable=False)  # list of subreddits targeted
    llm_config = Column(JSON, nullable=False)  # LLM settings used
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    source_documents = relationship("SourceDocument", back_populates="run", cascade="all, delete-orphan")
    pain_points = relationship("PainPoint", back_populates="run", cascade="all, delete-orphan")
    clusters = relationship("Cluster", back_populates="run", cascade="all, delete-orphan")
    trend_snapshots = relationship("TrendSnapshot", back_populates="run", cascade="all, delete-orphan")


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)  # "reddit", "github", etc.
    source_id = Column(String(255), nullable=False)  # external post/comment ID
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    created_at = Column(DateTime, nullable=False)  # Original post datetime in UTC
    raw_metadata = Column("metadata", JSON, nullable=False, default=dict)  # score, comments, subreddit, etc.
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    run = relationship("Run", back_populates="source_documents")
    pain_points = relationship("PainPoint", back_populates="source_document", cascade="all, delete-orphan")


class PainPoint(Base):
    __tablename__ = "pain_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    has_pain_point = Column(Boolean, nullable=False, default=False)
    summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # category constraint checked in logic
    intensity = Column(Integer, nullable=True)  # 1-5
    quoted_evidence = Column(Text, nullable=True)
    confidence = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    run = relationship("Run", back_populates="pain_points")
    source_document = relationship("SourceDocument", back_populates="pain_points")
    clusters = relationship("Cluster", secondary=cluster_evidence, back_populates="pain_points")


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    frequency = Column(Float, nullable=False, default=0.0)
    intensity = Column(Float, nullable=False, default=0.0)
    diversity = Column(Integer, nullable=False, default=0)
    persistence = Column(Float, nullable=False, default=0.0)
    duplicate_count = Column(Integer, nullable=False, default=0)
    duplicate_ids = Column(JSON, nullable=False, default=list)  # list of deduplicated pain point IDs
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    run = relationship("Run", back_populates="clusters")
    pain_points = relationship("PainPoint", secondary=cluster_evidence, back_populates="clusters")
    opportunities = relationship("Opportunity", back_populates="cluster", cascade="all, delete-orphan")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Integer, nullable=False, default=0)  # 0-100
    reasoning = Column(Text, nullable=False)
    is_valid = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    cluster = relationship("Cluster", back_populates="opportunities")
    ideas = relationship("Idea", back_populates="opportunity", cascade="all, delete-orphan")


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # micro_saas, ai_agent, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="ideas")


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)  # ollama, openai, anthropic, groq, gemini, openrouter, custom
    model = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False, default=dict)  # extra configs like temperature, base_url etc.
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    cluster_name = Column(String(255), nullable=False)
    frequency = Column(Float, nullable=False, default=0.0)
    snapshot_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    run = relationship("Run", back_populates="trend_snapshots")


class PipelineSettings(Base):
    """
    Persists the user's preferred subreddits and pipeline config across sessions.
    Only one active row is kept at a time (is_active=True).
    """
    __tablename__ = "pipeline_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subreddits = Column(JSON, nullable=False, default=list)
    feeds = Column(JSON, nullable=False, default=lambda: ["hot", "top", "rising", "new"])
    feed_limit = Column(Integer, nullable=False, default=100)
    comment_depth = Column(Integer, nullable=False, default=3)
    dedup_threshold = Column(Float, nullable=False, default=0.85)
    min_length = Column(Integer, nullable=False, default=40)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

