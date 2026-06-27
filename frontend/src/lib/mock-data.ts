/**
 * Bundled mock dataset.
 *
 * The frontend renders against this whenever the backend API is unreachable
 * or NEXT_PUBLIC_API_URL is not set. This keeps every page functional during
 * development and lets the real backend swap in transparently later.
 *
 * Mock data is intentionally clearly namespaced here so it can be removed in
 * one place when the backend is fully live.
 */

import type {
  Cluster,
  Idea,
  Opportunity,
  PainPoint,
  Run,
  Settings,
  SourceDocument,
  TrendSnapshot,
} from "./types";

export const mockRuns: Run[] = [
  {
    id: "run-001",
    status: "completed",
    subreddits: ["SaaS", "Entrepreneur", "smallbusiness", "sysadmin"],
    llm_config: { provider: "openai", model: "gpt-4o-mini" },
    error: null,
    created_at: "2026-06-20T10:12:00Z",
    updated_at: "2026-06-20T11:48:00Z",
  },
  {
    id: "run-002",
    status: "completed",
    subreddits: ["SaaS", "freelance", "sysadmin", "accounting"],
    llm_config: { provider: "openai", model: "gpt-4o-mini" },
    error: null,
    created_at: "2026-06-22T09:30:00Z",
    updated_at: "2026-06-22T10:55:00Z",
  },
  {
    id: "run-003",
    status: "running",
    subreddits: ["SaaS", "Entrepreneur", "smallbusiness", "devops"],
    llm_config: { provider: "anthropic", model: "claude-3-5-sonnet" },
    error: null,
    created_at: "2026-06-27T08:05:00Z",
    updated_at: "2026-06-27T08:05:00Z",
  },
  {
    id: "run-004",
    status: "failed",
    subreddits: ["SaaS", "marketing"],
    llm_config: { provider: "groq", model: "llama-3.1-70b" },
    error: "Rate limit exceeded during extract node (attempt 3/3).",
    created_at: "2026-06-25T14:20:00Z",
    updated_at: "2026-06-25T14:41:00Z",
  },
];

export const mockSourceDocuments: SourceDocument[] = [
  {
    id: "src-001",
    run_id: "run-002",
    source: "reddit",
    source_id: "1abc",
    title: "Invoicing software that doesn't suck?",
    content:
      "Every invoicing tool I've tried either breaks on multi-currency or makes me hand-enter line items. I waste 4 hours a week just reconciling.",
    author: "u/freelance_dev",
    url: "https://reddit.com/r/freelance/comments/1abc",
    created_at: "2026-06-21T16:02:00Z",
    metadata: { score: 312, comment_count: 88, subreddit: "freelance", feed: "hot" },
    collected_at: "2026-06-22T09:31:00Z",
  },
  {
    id: "src-002",
    run_id: "run-002",
    source: "reddit",
    source_id: "1def",
    title: null,
    content:
      "Spent the whole afternoon matching PDFs to bank statements manually. There has to be a better way.",
    author: "u/small_shop_owner",
    url: "https://reddit.com/r/smallbusiness/comments/1def",
    created_at: "2026-06-21T19:40:00Z",
    metadata: { score: 156, comment_count: 41, subreddit: "smallbusiness", feed: "top" },
    collected_at: "2026-06-22T09:31:00Z",
  },
  {
    id: "src-003",
    run_id: "run-002",
    source: "reddit",
    source_id: "1ghi",
    title: "Reconciliation tools are a nightmare",
    content:
      "Our accountant quit because the reconciliation workflow in [tool] is so manual. We need something that auto-matches transactions.",
    author: "u/bookkeeper_pain",
    url: "https://reddit.com/r/accounting/comments/1ghi",
    created_at: "2026-06-22T07:10:00Z",
    metadata: { score: 98, comment_count: 27, subreddit: "accounting", feed: "rising" },
    collected_at: "2026-06-22T09:31:00Z",
  },
  {
    id: "src-004",
    run_id: "run-001",
    source: "reddit",
    source_id: "1jkl",
    title: "Jira alternatives for small teams?",
    content:
      "Jira is so heavy. Half my team's time is spent updating tickets instead of building. We need a lighter workflow tool.",
    author: "u/dev_lead",
    url: "https://reddit.com/r/sysadmin/comments/1jkl",
    created_at: "2026-06-19T12:00:00Z",
    metadata: { score: 421, comment_count: 134, subreddit: "sysadmin", feed: "top" },
    collected_at: "2026-06-20T10:13:00Z",
  },
  {
    id: "src-005",
    run_id: "run-001",
    source: "reddit",
    source_id: "1mno",
    title: null,
    content:
      "Status meetings are useless when the tool doesn't sync with our actual git activity. I just want a dashboard that reads from commits.",
    author: "u/eng_manager",
    url: "https://reddit.com/r/SaaS/comments/1mno",
    created_at: "2026-06-19T15:22:00Z",
    metadata: { score: 204, comment_count: 58, subreddit: "SaaS", feed: "hot" },
    collected_at: "2026-06-20T10:13:00Z",
  },
];

export const mockPainPoints: PainPoint[] = [
  {
    id: "pp-001",
    run_id: "run-002",
    source_document_id: "src-001",
    has_pain_point: true,
    summary: "Manual invoice reconciliation wastes hours per week.",
    category: "data_entry",
    intensity: 4,
    quoted_evidence: "I waste 4 hours a week just reconciling.",
    confidence: 88,
    created_at: "2026-06-22T10:00:00Z",
    source_document: mockSourceDocuments[0],
  },
  {
    id: "pp-002",
    run_id: "run-002",
    source_document_id: "src-002",
    has_pain_point: true,
    summary: "Matching PDFs to bank statements is done by hand.",
    category: "workflow_bottleneck",
    intensity: 5,
    quoted_evidence: "Spent the whole afternoon matching PDFs to bank statements manually.",
    confidence: 92,
    created_at: "2026-06-22T10:00:00Z",
    source_document: mockSourceDocuments[1],
  },
  {
    id: "pp-003",
    run_id: "run-002",
    source_document_id: "src-003",
    has_pain_point: true,
    summary: "Reconciliation tools require manual transaction matching.",
    category: "bad_software",
    intensity: 4,
    quoted_evidence: "We need something that auto-matches transactions.",
    confidence: 81,
    created_at: "2026-06-22T10:00:00Z",
    source_document: mockSourceDocuments[2],
  },
  {
    id: "pp-004",
    run_id: "run-001",
    source_document_id: "src-004",
    has_pain_point: true,
    summary: "Project tools are too heavy; ticket updates eat dev time.",
    category: "workflow_bottleneck",
    intensity: 4,
    quoted_evidence: "Half my team's time is spent updating tickets instead of building.",
    confidence: 85,
    created_at: "2026-06-20T10:40:00Z",
    source_document: mockSourceDocuments[3],
  },
  {
    id: "pp-005",
    run_id: "run-001",
    source_document_id: "src-005",
    has_pain_point: true,
    summary: "Reporting doesn't sync with real engineering activity.",
    category: "reporting",
    intensity: 3,
    quoted_evidence: "I just want a dashboard that reads from commits.",
    confidence: 74,
    created_at: "2026-06-20T10:40:00Z",
    source_document: mockSourceDocuments[4],
  },
];

export const mockClusters: Cluster[] = [
  {
    id: "cl-001",
    run_id: "run-002",
    name: "Manual financial reconciliation",
    summary:
      "Small businesses and freelancers spend hours each week manually matching invoices, PDFs, and bank statements because existing tools don't auto-reconcile.",
    category: "data_entry",
    score: 84,
    frequency: 0.42,
    intensity: 4.3,
    diversity: 3,
    persistence: 0.78,
    duplicate_count: 14,
    duplicate_ids: ["pp-001", "pp-002", "pp-003"],
    created_at: "2026-06-22T10:20:00Z",
    pain_points: [mockPainPoints[0], mockPainPoints[1], mockPainPoints[2]],
  },
  {
    id: "cl-002",
    run_id: "run-001",
    name: "Heavyweight project tracking overhead",
    summary:
      "Engineering teams lose hours to ticket maintenance in tools like Jira; they want lightweight tracking that reflects real git activity.",
    category: "workflow_bottleneck",
    score: 72,
    frequency: 0.31,
    intensity: 3.8,
    diversity: 2,
    persistence: 0.65,
    duplicate_count: 9,
    duplicate_ids: ["pp-004", "pp-005"],
    created_at: "2026-06-20T11:00:00Z",
    pain_points: [mockPainPoints[3], mockPainPoints[4]],
  },
  {
    id: "cl-003",
    run_id: "run-001",
    name: "No lightweight on-call scheduling",
    summary: "Small ops teams lack simple, fair on-call rotation tools that integrate with chat.",
    category: "scheduling",
    score: 51,
    frequency: 0.18,
    intensity: 3.2,
    diversity: 2,
    persistence: 0.4,
    duplicate_count: 6,
    duplicate_ids: [],
    created_at: "2026-06-20T11:00:00Z",
    pain_points: [],
  },
];

export const mockOpportunities: Opportunity[] = [
  {
    id: "op-001",
    cluster_id: "cl-001",
    title: "Auto-reconciliation SaaS for small finance teams",
    summary:
      "A tool that ingests invoices + bank statements and auto-matches transactions, eliminating hours of manual reconciliation per week.",
    category: "data_entry",
    score: 84,
    confidence: 88,
    reasoning:
      "Recurring across 3 subreddits (freelance, smallbusiness, accounting), high intensity (4.3 avg), users actively frustrated, clear willingness to pay — bookkeepers and owners waste paid hours on this today.",
    is_valid: true,
    created_at: "2026-06-22T10:30:00Z",
    cluster: mockClusters[0],
    ideas: [],
  },
  {
    id: "op-002",
    cluster_id: "cl-002",
    title: "Git-native lightweight project tracker",
    summary:
      "A project tool that derives status from git activity instead of requiring manual ticket updates, aimed at small engineering teams.",
    category: "workflow_bottleneck",
    score: 72,
    confidence: 81,
    reasoning:
      "Strong signal in sysadmin and SaaS; developers openly resent ticket overhead. Diversity of 2 subreddits and persistence across runs support validity.",
    is_valid: true,
    created_at: "2026-06-20T11:10:00Z",
    cluster: mockClusters[1],
    ideas: [],
  },
  {
    id: "op-003",
    cluster_id: "cl-003",
    title: "Simple on-call rotation for small ops teams",
    summary:
      "Fair, lightweight on-call scheduling integrated with Slack/Teams for teams too small for PagerDuty.",
    category: "scheduling",
    score: 51,
    confidence: 62,
    reasoning:
      "Below diversity threshold (only 2 subreddits, low persistence). Kept for monitoring but flagged borderline per the reject-on-doubt rule.",
    is_valid: false,
    created_at: "2026-06-20T11:10:00Z",
    cluster: mockClusters[2],
    ideas: [],
  },
];

export const mockIdeas: Idea[] = [
  {
    id: "idea-001",
    opportunity_id: "op-001",
    type: "micro_saas",
    title: "ReconMatch",
    description:
      "Drop-in SaaS that connects to your bank and invoicing tool and auto-suggests transaction matches with confidence scores.",
    created_at: "2026-06-22T10:35:00Z",
    opportunity: mockOpportunities[0],
  },
  {
    id: "idea-002",
    opportunity_id: "op-001",
    type: "ai_agent",
    title: "Invoice-matching agent",
    description:
      "An AI agent that learns your matching rules and handles ambiguous transactions autonomously, escalating only edge cases.",
    created_at: "2026-06-22T10:35:00Z",
    opportunity: mockOpportunities[0],
  },
  {
    id: "idea-003",
    opportunity_id: "op-001",
    type: "service_business",
    title: "Boutique reconciliation service",
    description:
      "A done-for-you monthly reconciliation service layered on the same matching engine for clients who don't want software.",
    created_at: "2026-06-22T10:35:00Z",
    opportunity: mockOpportunities[0],
  },
  {
    id: "idea-004",
    opportunity_id: "op-002",
    type: "micro_saas",
    title: "CommitBoard",
    description:
      "A kanban that auto-moves cards from commit messages and PR merges — zero manual ticket updates.",
    created_at: "2026-06-20T11:15:00Z",
    opportunity: mockOpportunities[1],
  },
  {
    id: "idea-005",
    opportunity_id: "op-002",
    type: "chrome_extension",
    title: "Git-status badge",
    description:
      "Browser extension that overlays real build/commit status onto existing trackers so teams see truth, not stale tickets.",
    created_at: "2026-06-20T11:15:00Z",
    opportunity: mockOpportunities[1],
  },
];

export const mockTrendSnapshots: TrendSnapshot[] = [
  { id: "t-1", run_id: "run-001", cluster_name: "Manual financial reconciliation", frequency: 0.28, snapshot_date: "2026-06-20T11:48:00Z" },
  { id: "t-2", run_id: "run-002", cluster_name: "Manual financial reconciliation", frequency: 0.42, snapshot_date: "2026-06-22T10:55:00Z" },
  { id: "t-3", run_id: "run-001", cluster_name: "Heavyweight project tracking overhead", frequency: 0.26, snapshot_date: "2026-06-20T11:48:00Z" },
  { id: "t-4", run_id: "run-002", cluster_name: "Heavyweight project tracking overhead", frequency: 0.31, snapshot_date: "2026-06-22T10:55:00Z" },
  { id: "t-5", run_id: "run-001", cluster_name: "No lightweight on-call scheduling", frequency: 0.12, snapshot_date: "2026-06-20T11:48:00Z" },
  { id: "t-6", run_id: "run-002", cluster_name: "No lightweight on-call scheduling", frequency: 0.18, snapshot_date: "2026-06-22T10:55:00Z" },
];

export const mockSettings: Settings = {
  llm_config: {
    id: "llm-001",
    provider: "openai",
    model: "gpt-4o-mini",
    config: { temperature: 0.2 },
    is_active: true,
    created_at: "2026-06-18T09:00:00Z",
  },
  subreddits: ["SaaS", "Entrepreneur", "smallbusiness", "freelance", "sysadmin"],
  pipeline: {
    feeds: ["hot", "top", "rising", "new"],
    feed_limit: 100,
    comment_depth: 3,
    dedup_threshold: 0.85,
    min_length: 40,
    validation: {
      min_unique_mentions: 10,
      min_unique_users: 3,
      min_unique_threads: 2,
      min_avg_confidence: 2,
    },
  },
};
