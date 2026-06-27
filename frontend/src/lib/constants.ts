/**
 * Display labels + helpers for the category and idea-type unions from AGENTS.md.
 * Centralized so badges/selects stay consistent across pages.
 */

import type { Category, IdeaType } from "./types";

export const CATEGORY_LABELS: Record<Category, string> = {
  manual_work: "Manual Work",
  missing_software: "Missing Software",
  bad_software: "Bad Software",
  workflow_bottleneck: "Workflow Bottleneck",
  reporting: "Reporting",
  compliance: "Compliance",
  data_entry: "Data Entry",
  automation: "Automation",
  communication: "Communication",
  scheduling: "Scheduling",
  integration_gap: "Integration Gap",
  expensive_service: "Expensive Service",
};

export const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
  value: value as Category,
  label,
}));

export const IDEA_TYPE_LABELS: Record<IdeaType, string> = {
  micro_saas: "Micro-SaaS",
  ai_agent: "AI Agent",
  chrome_extension: "Chrome Extension",
  api_product: "API Product",
  marketplace: "Marketplace",
  service_business: "Service Business",
  internal_tool: "Internal Tool",
  workflow_automation: "Workflow Automation",
};

export const IDEA_TYPE_OPTIONS = Object.entries(IDEA_TYPE_LABELS).map(([value, label]) => ({
  value: value as IdeaType,
  label,
}));

export const PROVIDER_OPTIONS = [
  "ollama",
  "openai",
  "anthropic",
  "groq",
  "gemini",
  "openrouter",
  "custom",
] as const;

/** Map a 0-100 score to a Tailwind color token for badges. */
export function scoreColor(score: number): string {
  if (score >= 75) return "text-emerald-600";
  if (score >= 50) return "text-amber-600";
  return "text-rose-600";
}

/** Map a 0-100 score to a short qualitative label. */
export function scoreLabel(score: number): string {
  if (score >= 75) return "Strong";
  if (score >= 50) return "Moderate";
  return "Weak";
}
