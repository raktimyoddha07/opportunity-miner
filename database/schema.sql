-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Runs Table
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    subreddits JSONB NOT NULL,
    llm_config JSONB NOT NULL,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 2. Source Documents Table
CREATE TABLE IF NOT EXISTS source_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    title VARCHAR(512),
    content TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    url VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 3. Pain Points Table
CREATE TABLE IF NOT EXISTS pain_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    source_document_id UUID NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    has_pain_point BOOLEAN NOT NULL DEFAULT FALSE,
    summary TEXT,
    category VARCHAR(100),
    intensity INTEGER,
    quoted_evidence TEXT,
    confidence INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 4. Clusters Table
CREATE TABLE IF NOT EXISTS clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    frequency DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    intensity DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    diversity INTEGER NOT NULL DEFAULT 0,
    persistence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    duplicate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 5. Cluster Evidence Table (Many-to-Many Association)
CREATE TABLE IF NOT EXISTS cluster_evidence (
    cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    pain_point_id UUID NOT NULL REFERENCES pain_points(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, pain_point_id)
);

-- 6. Opportunities Table
CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence INTEGER NOT NULL DEFAULT 0,
    reasoning TEXT NOT NULL,
    is_valid BOOLEAN NOT NULL DEFAULT FALSE,
    external_signals JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 7. Ideas Table
CREATE TABLE IF NOT EXISTS ideas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 8. LLM Configs Table
CREATE TABLE IF NOT EXISTS llm_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);

-- 9. Trend Snapshots Table
CREATE TABLE IF NOT EXISTS trend_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    cluster_name VARCHAR(255) NOT NULL,
    frequency DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    snapshot_date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()) NOT NULL
);
