/**
 * Typed API client for the Reddit Opportunity Miner backend.
 *
 * Routes match AGENTS.md (FastAPI Routes). When NEXT_PUBLIC_API_URL is unset or
 * a request fails, every function falls back to bundled mock data and logs a
 * warning — the UI never crashes because the backend is unreachable.
 *
 * Per AGENTS.md: the source-of-truth is the database of validated problems;
 * the frontend only reads it. Mutations (start run, save settings) are best
 * effort and surface errors to the caller.
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
import * as mock from "./mock-data";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

/** True when no backend URL is configured (mock mode). */
export const usingMocks = BASE_URL === "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
    // Never cache list/detail reads — the database grows continuously.
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return (await res.json()) as T;
}

/**
 * Wrap a real API call; on any error, log and return mock fallback.
 * Used for read endpoints so a down backend never breaks the UI.
 */
async function withFallback<T>(real: () => Promise<T>, fallback: T, label: string): Promise<T> {
  if (usingMocks) return fallback;
  try {
    return await real();
  } catch (err) {
    console.warn(`[api] ${label} failed, using mock data:`, err);
    return fallback;
  }
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export async function getRuns(): Promise<Run[]> {
  return withFallback(() => request<Run[]>("/runs"), mock.mockRuns, "getRuns");
}

export async function getRun(id: string): Promise<Run | null> {
  const fallback = mock.mockRuns.find((r) => r.id === id) ?? null;
  return withFallback(() => request<Run>(`/runs/${id}`), fallback, "getRun");
}

export async function startRun(payload: {
  subreddits: string[];
  llm_config?: Record<string, unknown>;
}): Promise<Run | null> {
  if (usingMocks) {
    return {
      id: `run-${Date.now()}`,
      status: "running",
      subreddits: payload.subreddits,
      llm_config: payload.llm_config ?? {},
      error: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }
  // Mutations surface errors to the caller (no silent mock fallback here).
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
  if (usingMocks) return;
  const res = await fetch(`${BASE_URL}/runs/${id}`, { method: "DELETE", cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to delete run: ${res.status}`);
}

export async function stopRun(id: string): Promise<Run | null> {
  if (usingMocks) {
    const run = mock.mockRuns.find((r) => r.id === id);
    if (run) {
      run.status = "failed";
      run.error = "Stopped by user";
    }
    return run ?? null;
  }
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
  return withFallback(
    () => request<Opportunity[]>("/opportunities"),
    mock.mockOpportunities,
    "getOpportunities",
  );
}

export async function getOpportunity(id: string): Promise<Opportunity | null> {
  const fallback = mock.mockOpportunities.find((o) => o.id === id) ?? null;
  return withFallback(() => request<Opportunity>(`/opportunities/${id}`), fallback, "getOpportunity");
}

// ---------------------------------------------------------------------------
// Clusters
// ---------------------------------------------------------------------------

export async function getClusters(): Promise<Cluster[]> {
  return withFallback(() => request<Cluster[]>("/clusters"), mock.mockClusters, "getClusters");
}

export async function getCluster(id: string): Promise<Cluster | null> {
  const fallback = mock.mockClusters.find((c) => c.id === id) ?? null;
  return withFallback(() => request<Cluster>(`/clusters/${id}`), fallback, "getCluster");
}

// ---------------------------------------------------------------------------
// Evidence (pain points + their source documents — the trust layer)
// ---------------------------------------------------------------------------

export async function getEvidence(clusterId?: string): Promise<PainPoint[]> {
  if (clusterId) {
    const fallback = mock.mockPainPoints.filter(
      (p) => mock.mockClusters.find((c) => c.id === clusterId)?.duplicate_ids.includes(p.id),
    );
    return withFallback(
      () => request<PainPoint[]>(`/evidence?cluster_id=${clusterId}`),
      fallback,
      "getEvidence(cluster)",
    );
  }
  return withFallback(() => request<PainPoint[]>("/evidence"), mock.mockPainPoints, "getEvidence");
}

export async function getSourceDocuments(): Promise<SourceDocument[]> {
  return withFallback(
    () => request<SourceDocument[]>("/evidence/sources"),
    mock.mockSourceDocuments,
    "getSourceDocuments",
  );
}

// ---------------------------------------------------------------------------
// Ideas
// ---------------------------------------------------------------------------

export async function getIdeas(): Promise<Idea[]> {
  return withFallback(() => request<Idea[]>("/ideas"), mock.mockIdeas, "getIdeas");
}

export async function getIdea(id: string): Promise<Idea | null> {
  const fallback = mock.mockIdeas.find((i) => i.id === id) ?? null;
  return withFallback(() => request<Idea>(`/ideas/${id}`), fallback, "getIdea");
}

export async function generateIdeas(opportunityId: string): Promise<Idea[] | null> {
  if (usingMocks) {
    return mock.mockIdeas.filter((i) => i.opportunity_id === opportunityId);
  }
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
  return withFallback(
    () => request<TrendSnapshot[]>("/trends"),
    mock.mockTrendSnapshots,
    "getTrendSnapshots",
  );
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export async function getSettings(): Promise<Settings> {
  return withFallback(() => request<Settings>("/settings"), mock.mockSettings, "getSettings");
}

export async function saveSettings(settings: Settings): Promise<Settings> {
  if (usingMocks) return settings;
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
  return withFallback(() => request<JsonExport>("/export/json"), {
    opportunities: mock.mockOpportunities,
    clusters: mock.mockClusters,
    evidence: mock.mockPainPoints,
    ideas: mock.mockIdeas,
  }, "getJsonExport");
}
