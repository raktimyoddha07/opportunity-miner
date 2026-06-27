"""
Scoring service.

Pure helper functions for computing the opportunity score signals described in
AGENTS.md. The pipeline `score` node uses these inline (it also persists), but
the service layer exposes them so the API/services can re-score or preview
scores without re-running the whole pipeline.

Opportunity Score = Frequency * Intensity * Diversity * Persistence, 0-100.
"""


def compute_frequency(cluster_mentions: int, total_mentions: int) -> float:
    """mentions / total_mentions, clamped to [0, 1]."""
    if total_mentions <= 0:
        return 0.0
    return min(cluster_mentions / float(total_mentions), 1.0)


def compute_intensity(intensities: list[int]) -> float:
    """Average intensity (1-5) normalized to [0, 1]."""
    vals = [i for i in intensities if i is not None]
    if not vals:
        return 0.0
    avg = sum(vals) / len(vals)
    return min(max(avg / 5.0, 0.0), 1.0)


def compute_diversity(subreddits: list[str]) -> float:
    """Unique-subreddit count normalized against a 5-subreddit saturation cap."""
    unique = {s for s in subreddits if s}
    return min(len(unique) / 5.0, 1.0)


def compute_persistence(days: list) -> float:
    """Distinct calendar days spanned, normalized against a 3-day saturation cap."""
    unique = set()
    for d in days:
        if hasattr(d, "date"):
            unique.add(d.date())
        elif d:
            unique.add(d)
    return min(len(unique) / 3.0, 1.0)


def opportunity_score(frequency: float, intensity: float,
                      diversity: float, persistence: float) -> float:
    """Compose the four normalized sub-signals into a 0-100 score."""
    raw = frequency * intensity * diversity * persistence
    return round(raw * 100.0, 2)
