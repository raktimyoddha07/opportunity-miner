/**
 * Mock data disabled. The application now operates strictly on real database data.
 */
export const mockRuns = [];
export const mockSourceDocuments = [];
export const mockPainPoints = [];
export const mockClusters = [];
export const mockOpportunities = [];
export const mockIdeas = [];
export const mockTrendSnapshots = [];
export const mockSettings = {
  llm_config: {
    provider: "ollama",
    model: "qwen2.5:7b-instruct",
    config: { base_url: "http://localhost:11434" },
    is_active: true,
  },
  subreddits: [],
  pipeline: {
    feeds: ["hot", "top", "rising", "new"],
    feed_limit: 100,
    comment_depth: 3,
    dedup_threshold: 0.85,
    min_length: 40,
    validation: {
      min_unique_mentions: 3,
      min_unique_users: 2,
      min_unique_threads: 1,
      min_avg_confidence: 1.5,
    },
  },
};
