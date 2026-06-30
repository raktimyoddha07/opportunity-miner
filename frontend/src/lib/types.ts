/**
 * TypeScript domain types — mirror of backend/db/models.py.
 *
 * These are the single source of truth for the frontend's data shapes.
 * When the backend contract changes in models.py, update this file to match.
 * See AGENTS.md for the full schema description.
 */

/** Allowed pain-point categories (AGENTS.md: Pain Point Categories). */
export type Category =
  | "manual_work"
  | "missing_software"
  | "bad_software"
  | "workflow_bottleneck"
  | "reporting"
  | "compliance"
  | "data_entry"
  | "automation"
  | "communication"
  | "scheduling"
  | "integration_gap"
  | "expensive_service";

/** Allowed idea types (AGENTS.md: Idea Types). */
export type IdeaType =
  | "micro_saas"
  | "ai_agent"
  | "chrome_extension"
  | "api_product"
  | "marketplace"
  | "service_business"
  | "internal_tool"
  | "workflow_automation";

/** Supported LLM providers (AGENTS.md: LLM Factory). */
export type Provider =
  | "ollama"
  | "openai"
  | "anthropic"
  | "groq"
  | "gemini"
  | "openrouter"
  | "custom";

export type RunStatus = "running" | "completed" | "failed";

/** Extra fields carried on a source document's metadata (score, subreddit, etc.). */
export interface SourceMetadata {
  score?: number;
  comment_count?: number;
  subreddit?: string;
  permalink?: string;
  feed?: "hot" | "top" | "rising" | "new";
  [key: string]: unknown;
}

/** runs table */
export interface Run {
  id: string;
  status: RunStatus;
  subreddits: string[];
  llm_config: Record<string, unknown>;
  error: string | null;
  created_at: string;
  updated_at: string;
}

/** source_documents table — the raw, never-discarded source of truth. */
export interface SourceDocument {
  id: string;
  run_id: string;
  source: "reddit" | "github" | "hackernews" | "g2" | string;
  source_id: string;
  title: string | null;
  content: string;
  author: string;
  url: string;
  created_at: string; // original post datetime, UTC
  metadata: SourceMetadata;
  collected_at: string;
}

/** pain_points table */
export interface PainPoint {
  id: string;
  run_id: string;
  source_document_id: string;
  has_pain_point: boolean;
  summary: string | null;
  category: Category | null;
  emotion: string | null;   // one of 8 emotion taxonomy values (e.g. "paying_for_bad_tool")
  intensity: number | null; // 1-5
  quoted_evidence: string | null;
  confidence: number | null; // 0-100
  created_at: string;
  /** Joined source document for display (evidence list / detail). */
  source_document?: SourceDocument;
}

/** clusters table */
export interface Cluster {
  id: string;
  run_id: string;
  name: string;
  summary: string;
  category: Category;
  score: number; // 0-100
  frequency: number; // 0-1
  intensity: number; // 1-5 avg
  diversity: number; // unique subreddits
  persistence: number; // 0-1
  duplicate_count: number;
  duplicate_ids: string[];
  created_at: string;
  pain_points?: PainPoint[];
}

/** opportunities table — a validated cluster. */
export interface Opportunity {
  id: string;
  cluster_id: string;
  title: string;
  summary: string;
  category: Category;
  score: number; // 0-100
  confidence: number; // 0-100
  reasoning: string;
  is_valid: boolean;
  external_signals?: Record<string, unknown>;
  created_at: string;
  cluster?: Cluster;
  ideas?: Idea[];
}

/** ideas table */
export interface Idea {
  id: string;
  opportunity_id: string;
  type: IdeaType;
  title: string;
  description: string;
  created_at: string;
  opportunity?: Opportunity;
}

/** llm_configs table */
export interface LLMConfig {
  id: string;
  provider: Provider;
  model: string;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

/** trend_snapshots table — per-run frequency snapshots for trend detection. */
export interface TrendSnapshot {
  id: string;
  run_id: string;
  cluster_name: string;
  frequency: number;
  snapshot_date: string;
}

/** Settings payload exchanged with POST/GET /settings. */
export interface Settings {
  llm_config: LLMConfig;
  subreddits: string[];
  pipeline: {
    feeds: ("hot" | "top" | "rising" | "new")[];
    feed_limit: number;
    comment_depth: number;
    dedup_threshold: number; // embedding similarity, default 0.85
    min_length: number; // content min length, default 40
    validation: {
      min_unique_mentions: number; // 10
      min_unique_users: number; // 3
      min_unique_threads: number; // 2
      min_avg_confidence: number; // 2
    };
  };
}

/** Generic API list wrapper returned by collection endpoints. */
export interface ApiResponse<T> {
  data: T;
}

/** Shape of the JSON export (AGENTS.md: Export Formats). */
export interface JsonExport {
  opportunities: Opportunity[];
  clusters: Cluster[];
  evidence: PainPoint[];
  ideas: Idea[];
}
