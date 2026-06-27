"""
Clustering service.

Provides richer, reusable clustering utilities used both by the pipeline
`cluster` node (which persists results) and by the API layer for on-demand
re-grouping or analysis previews.

Two strategies are offered:
  - group_by_category: trivial categorical bucketing
  - semantic_cluster: embedding-based clustering with a greedy connected-component
    pass (no sklearn dependency required; falls back to token Jaccard when no
    embeddings are available)

Source-agnostic: operates purely on pain point dicts.
"""
from collections import defaultdict
from typing import Callable, Optional


def group_by_category(pain_points: list[dict]) -> dict[str, list[dict]]:
    """Bucket pain points by their `category` field."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for pp in pain_points:
        buckets[pp.get("category") or "uncategorized"].append(pp)
    return dict(buckets)


def _tokenize(text: str) -> set[str]:
    return {tok for tok in (text or "").lower().split() if len(tok) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def semantic_cluster(
    pain_points: list[dict],
    embed_fn: Optional[Callable[[list[str]], object]] = None,
    threshold: float = 0.85,
) -> list[list[dict]]:
    """
    Group pain points into clusters using embedding similarity (preferred) or a
    Jaccard token-overlap fallback.

    embed_fn: callable mapping list[text] -> (n, d) numpy array. If None or if
              it raises, the Jaccard fallback is used.
    threshold: similarity above which two points join the same cluster.

    Returns a list of clusters, each a list of pain point dicts.
    """
    candidates = list(pain_points)
    if not candidates:
        return []

    sim = None
    if embed_fn is not None:
        try:
            import numpy as np  # noqa
            vectors = embed_fn([pp.get("summary", "") for pp in candidates])
            if vectors is not None and getattr(vectors, "shape", (0,))[0] == len(candidates):
                import numpy as np
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                normed = vectors / norms
                sim = normed @ normed.T
        except Exception as e:
            print(f"semantic_cluster embedding path failed, using Jaccard: {e}")
            sim = None

    n = len(candidates)
    assigned = [False] * n
    clusters: list[list[dict]] = []

    for i in range(n):
        if assigned[i]:
            continue
        assigned[i] = True
        group = [candidates[i]]
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            if sim is not None:
                score = float(sim[i, j])
            else:
                score = _jaccard(_tokenize(candidates[i].get("summary", "")),
                                 _tokenize(candidates[j].get("summary", "")))
            if score >= threshold:
                assigned[j] = True
                group.append(candidates[j])
        clusters.append(group)

    return clusters


def name_cluster(category: str, members: list[dict]) -> str:
    """Derive a human-readable cluster name from its members."""
    rep = max(members, key=lambda p: (p.get("confidence") or 0, p.get("intensity") or 0))
    summary = rep.get("summary") or rep.get("quoted_evidence") or category
    head = " ".join(summary.strip().split()[:6])
    label = category.replace("_", " ").title()
    return f"{label}: {head}" if head else label
