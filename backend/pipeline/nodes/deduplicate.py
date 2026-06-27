"""
Deduplicate pipeline node.

Contract (see AGENTS.md Node Contracts):
  Input  key: pain_points
  Output key: deduplicated_pain_points
  Uses LLM: No (embeddings)

Strategy:
  - Keep only pain points that actually express a pain point (has_pain_point=True).
  - Embed each pain point summary.
  - Greedily group summaries whose cosine similarity is >= the configured
    deduplication threshold (default 0.85, see config.DEFAULT_DEDUPLICATION_THRESHOLD).
  - For every duplicate group, keep ONE master pain point and attach a
    `duplicate_count` plus `duplicate_ids` list so the chain of evidence stays intact.

This node never aborts the run. On any failure it logs the error, stores it in
PipelineState.error, and returns whatever pain points it could safely pass through.
"""
import os
from typing import Optional

import numpy as np

from backend.config import settings
from backend.pipeline.state import PipelineState


def _load_prompt_dir() -> str:
    # Resolve backend/ directory regardless of cwd
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def embed_texts(texts: list[str], llm_config: dict) -> Optional[np.ndarray]:
    """
    Embed a list of strings into a (n, d) numpy matrix.

    Provider-agnostic: tries Ollama embeddings first (local), then OpenAI,
    then a deterministic local hashing fallback so the pipeline still runs in
    offline/test environments without an embedding API key.

    Returns None if embedding is entirely unavailable.
    """
    if not texts:
        return np.zeros((0, 1), dtype="float32")

    provider = (llm_config or {}).get("provider", "").lower()
    embedding_model = (llm_config or {}).get("embedding_model")

    # 1. Ollama local embeddings
    if provider == "ollama" or (llm_config or {}).get("embedding_provider") == "ollama":
        try:
            from langchain_community.embeddings import OllamaEmbeddings

            base_url = (llm_config or {}).get("base_url") or settings.OLLAMA_BASE_URL
            model = embedding_model or "nomic-embed-text"
            emb = OllamaEmbeddings(base_url=base_url, model=model)
            vectors = emb.embed_documents(texts)
            return np.asarray(vectors, dtype="float32")
        except Exception as e:
            print(f"Ollama embeddings unavailable, falling back: {e}")

    # 2. OpenAI embeddings
    if provider == "openai" or (llm_config or {}).get("embedding_provider") == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings

            api_key = (llm_config or {}).get("api_key") or settings.OPENAI_API_KEY
            model = embedding_model or "text-embedding-3-small"
            emb = OpenAIEmbeddings(api_key=api_key, model=model)
            vectors = emb.embed_documents(texts)
            return np.asarray(vectors, dtype="float32")
        except Exception as e:
            print(f"OpenAI embeddings unavailable, falling back: {e}")

    # 3. Deterministic hashing fallback (no network, stable across runs)
    return _hashing_embeddings(texts)


def _hashing_embeddings(texts: list[str], dim: int = 256) -> np.ndarray:
    """
    Lightweight deterministic embedding via signed feature hashing.

    Not semantically rich, but stable, dependency-free, and good enough to
    collapse near-identical summaries (same wording hashes to the same vector).
    Cosine similarity remains a sensible dedup signal.
    """
    import hashlib

    matrix = np.zeros((len(texts), dim), dtype="float32")
    for i, text in enumerate(texts):
        tokens = (text or "").lower().split()
        for tok in tokens:
            h = hashlib.md5(tok.encode("utf-8")).digest()
            bucket = int.from_bytes(h[:4], "little") % dim
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            matrix[i, bucket] += sign
    # L2-normalize rows so cosine similarity is just dot product
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _cosine_matrix(vectors: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity for row-vectors already L2-normalized."""
    if vectors.shape[0] == 0:
        return np.zeros((0, 0), dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = vectors / norms
    return normalized @ normalized.T


def deduplicate_pain_points(
    pain_points: list[dict],
    threshold: float,
    llm_config: dict,
) -> list[dict]:
    """
    Group pain points by embedding similarity.

    Returns a list of master pain point dicts; each carries
    `duplicate_count` (>= 1) and `duplicate_ids` (list of UUIDs merged into it).
    """
    # Only consider genuine pain points for deduplication
    candidates = [pp for pp in pain_points if pp.get("has_pain_point")]
    if not candidates:
        return []

    summaries = [pp.get("summary") or pp.get("quoted_evidence") or "" for pp in candidates]

    try:
        vectors = embed_texts(summaries, llm_config)
        sim = _cosine_matrix(vectors) if vectors is not None and vectors.shape[0] > 0 else None
    except Exception as e:
        print(f"Embedding/similarity failed, skipping dedup pass-through: {e}")
        # Safe fallback: treat each pain point as unique (no dedup)
        sim = None

    n = len(candidates)
    assigned: list[bool] = [False] * n
    masters: list[dict] = []

    for i in range(n):
        if assigned[i]:
            continue
        assigned[i] = True
        master = dict(candidates[i])
        group_ids = [candidates[i].get("id")]

        if sim is not None:
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                if float(sim[i, j]) >= threshold:
                    assigned[j] = True
                    group_ids.append(candidates[j].get("id"))

        master["duplicate_count"] = len(group_ids)
        master["duplicate_ids"] = group_ids
        masters.append(master)

    return masters


def deduplicate_node(state: PipelineState) -> dict:
    """
    Greedy embedding-similarity deduplication of extracted pain points.
    Input:  pain_points
    Output: deduplicated_pain_points
    """
    pain_points = state.get("pain_points", [])
    llm_config = state.get("llm_config", {})

    if not pain_points:
        return {"deduplicated_pain_points": []}

    try:
        threshold = settings.DEFAULT_DEDUPLICATION_THRESHOLD
        deduped = deduplicate_pain_points(pain_points, threshold, llm_config)
        original_count = len([pp for pp in pain_points if pp.get("has_pain_point")])
        print(f"Dedup: {original_count} pain points -> {len(deduped)} unique")
        return {"deduplicated_pain_points": deduped}
    except Exception as e:
        error_msg = f"Deduplicate node error: {e}"
        print(error_msg)
        # Never abort: pass through the raw pain points unchanged
        passthrough = [pp for pp in pain_points if pp.get("has_pain_point")]
        for pp in passthrough:
            pp.setdefault("duplicate_count", 1)
            pp.setdefault("duplicate_ids", [pp.get("id")])
        return {"deduplicated_pain_points": passthrough, "error": error_msg}
