/**
 * Typed API client for the Reddit Opportunity Miner backend.
 *
 * Routes match AGENTS.md (FastAPI Routes).
 * Direct connections to backend without mock fallback.
 */

import type {
  Cluster,
  Idea,
  JsonExport,
  Opportunity,
  PainPoint,
  Run,
  Settings,
  SourceDocument,
  TrendSnapshot,
} from "./types";

// API_URL is the server-side-only base URL (not exposed to the browser).
// NEXT_PUBLIC_API_URL is the fallback used for client-side fetches.
const BASE_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
    // Never cache list/detail reads — the database grows continuously.
    cache: "no-store",
    // Fail fast — don't wait 300 s for a backend that's down.
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export async function getRuns(): Promise<Run[]> {
  return request<Run[]>("/runs");
}

export async function getRun(id: string): Promise<Run | null> {
  return request<Run>(`/runs/${id}`);
}

export async function startRun(payload: {
  subreddits: string[];
  llm_config?: Record<string, unknown>;
}): Promise<Run | null> {
  const res = await fetch(`${BASE_URL}/runs/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to start run: ${res.status}`);
  return (await res.json()) as Run;
}

export async function deleteRun(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/runs/${id}`, { method: "DELETE", cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to delete run: ${res.status}`);
}

export async function stopRun(id: string): Promise<Run | null> {
  const res = await fetch(`${BASE_URL}/runs/${id}/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to stop run: ${res.status}`);
  return (await res.json()) as Run;
}

// ---------------------------------------------------------------------------
// Opportunities
// ---------------------------------------------------------------------------

export async function getOpportunities(): Promise<Opportunity[]> {
  return request<Opportunity[]>("/opportunities");
}

export async function getOpportunity(id: string): Promise<Opportunity | null> {
  return request<Opportunity>(`/opportunities/${id}`);
}

// ---------------------------------------------------------------------------
// Clusters
// ---------------------------------------------------------------------------

export async function getClusters(): Promise<Cluster[]> {
  return request<Cluster[]>("/clusters");
}

export async function getCluster(id: string): Promise<Cluster | null> {
  return request<Cluster>(`/clusters/${id}`);
}

// ---------------------------------------------------------------------------
// Evidence (pain points + their source documents — the trust layer)
// ---------------------------------------------------------------------------

export async function getEvidence(clusterId?: string): Promise<PainPoint[]> {
  if (clusterId) {
    return request<PainPoint[]>(`/evidence?cluster_id=${clusterId}`);
  }
  return request<PainPoint[]>("/evidence");
}

export async function getSourceDocuments(): Promise<SourceDocument[]> {
  return request<SourceDocument[]>("/evidence/sources");
}

// ---------------------------------------------------------------------------
// Ideas
// ---------------------------------------------------------------------------

export async function getIdeas(): Promise<Idea[]> {
  return request<Idea[]>("/ideas");
}

export async function getIdea(id: string): Promise<Idea | null> {
  return request<Idea>(`/ideas/${id}`);
}

export async function generateIdeas(opportunityId: string): Promise<Idea[] | null> {
  const res = await fetch(`${BASE_URL}/ideas/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ opportunity_id: opportunityId }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to generate ideas: ${res.status}`);
  return (await res.json()) as Idea[];
}

// ---------------------------------------------------------------------------
// Trends
// ---------------------------------------------------------------------------

export async function getTrendSnapshots(): Promise<TrendSnapshot[]> {
  return request<TrendSnapshot[]>("/trends");
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export async function getSettings(): Promise<Settings> {
  return request<Settings>("/settings");
}

export async function saveSettings(settings: Settings): Promise<Settings> {
  const res = await fetch(`${BASE_URL}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to save settings: ${res.status}`);
  return (await res.json()) as Settings;
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export function exportUrl(format: "csv" | "json" | "markdown"): string {
  return `${BASE_URL}/export/${format}`;
}

export async function getJsonExport(): Promise<JsonExport> {
  return request<JsonExport>("/export/json");
}
