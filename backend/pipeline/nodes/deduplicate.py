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


# Lazy singleton for all-MiniLM-L6-v2
_minilm_model = None


def _get_minilm():
    global _minilm_model
    if _minilm_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("[deduplicate] Loading all-MiniLM-L6-v2 embeddings model...")
            _minilm_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[deduplicate] all-MiniLM-L6-v2 loaded.")
        except Exception as e:
            print(f"[deduplicate] all-MiniLM-L6-v2 unavailable: {e}")
            _minilm_model = False  # sentinel
    return _minilm_model if _minilm_model else None


def embed_texts(texts: list[str], llm_config: dict) -> Optional[np.ndarray]:
    """
    Embed a list of strings into a (n, d) numpy matrix.

    Priority:
      1. all-MiniLM-L6-v2 via sentence-transformers (CPU, local, best quality)
      2. Deterministic hashing fallback (no dependencies, stable)
    """
    if not texts:
        return np.zeros((0, 1), dtype="float32")

    # 1. all-MiniLM-L6-v2 — best semantic similarity for short complaint texts
    model = _get_minilm()
    if model is not None:
        try:
            vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return np.asarray(vectors, dtype="float32")
        except Exception as e:
            print(f"[deduplicate] MiniLM encoding failed, using hashing fallback: {e}")

    # 2. Deterministic hashing fallback (no network, stable across runs)
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


from backend.db.connection import SessionLocal
from backend.db.models import PainPoint, Cluster

def _tokenize(text: str) -> set[str]:
    return {tok for tok in (text or "").lower().split() if len(tok) > 2}

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def deduplicate_node(state: PipelineState) -> dict:
    """
    Greedy embedding-similarity deduplication of extracted pain points.
    Input:  pain_points
    Output: deduplicated_pain_points
    """
    pain_points = state.get("pain_points", [])
    llm_config = state.get("llm_config", {})
    run_id = state.get("run_id")
    stats = state.get("pipeline_stats") or {}

    if not pain_points:
        stats["deduplicate_unique"] = 0
        print("[DEDUPLICATE]  → 0 unique clusters")
        return {"deduplicated_pain_points": [], "pipeline_stats": stats}

    # Separate current candidates
    candidates = [pp for pp in pain_points if pp.get("has_pain_point")]
    if not candidates:
        stats["deduplicate_unique"] = 0
        print("[DEDUPLICATE]  → 0 unique clusters")
        return {"deduplicated_pain_points": [], "pipeline_stats": stats}

    db = SessionLocal()
    try:
        # Load historical pain points
        historical_rows = db.query(PainPoint).filter(
            PainPoint.has_pain_point == True,
            PainPoint.run_id != run_id
        ).all()
        
        # Build embedding lists
        historical_pps = []
        for p in historical_rows:
            historical_pps.append({
                "id": str(p.id),
                "summary": p.summary or p.quoted_evidence or "",
                "orm_obj": p
            })

        threshold = settings.DEFAULT_DEDUPLICATION_THRESHOLD
        matched_count = 0
        
        # We need to embed everything for comparison
        all_summaries = [c.get("summary") or c.get("quoted_evidence") or "" for c in candidates]
        hist_summaries = [hp["summary"] for hp in historical_pps]
        
        sim_matrix = None
        # If we have historical data, embed and compare
        if hist_summaries and all_summaries:
            cand_vectors = embed_texts(all_summaries, llm_config)
            hist_vectors = embed_texts(hist_summaries, llm_config)
            
            if cand_vectors is not None and hist_vectors is not None:
                # Pairwise cosine similarity matrix of candidates (rows) and historical (columns)
                cand_norms = np.linalg.norm(cand_vectors, axis=1, keepdims=True)
                cand_norms[cand_norms == 0] = 1.0
                cand_normed = cand_vectors / cand_norms
                
                hist_norms = np.linalg.norm(hist_vectors, axis=1, keepdims=True)
                hist_norms[hist_norms == 0] = 1.0
                hist_normed = hist_vectors / hist_norms
                
                sim_matrix = cand_normed @ hist_normed.T
                
                # Check for matches
                non_duplicate_candidates = []
                for idx, cand in enumerate(candidates):
                    best_match_idx = int(np.argmax(sim_matrix[idx]))
                    best_score = float(sim_matrix[idx, best_match_idx])
                    
                    if best_score >= threshold:
                        # Match found! Link to historical clusters
                        hist_match = historical_pps[best_match_idx]["orm_obj"]
                        curr_orm = db.query(PainPoint).filter(PainPoint.id == cand["id"]).first()
                        if curr_orm and hist_match.clusters:
                            for cluster in hist_match.clusters:
                                if curr_orm not in cluster.pain_points:
                                    cluster.pain_points.append(curr_orm)
                                    cluster.duplicate_count += 1
                            db.flush()
                        matched_count += 1
                    else:
                        non_duplicate_candidates.append(cand)
                candidates = non_duplicate_candidates

        # Fallback Jaccard check if candidates and historical weren't compared yet (e.g. embeddings failed)
        if hist_summaries and candidates and sim_matrix is None:
            non_duplicate_candidates = []
            for cand in candidates:
                cand_tokens = _tokenize(cand.get("summary") or cand.get("quoted_evidence") or "")
                matched = False
                for hp in historical_pps:
                    hp_tokens = _tokenize(hp["summary"])
                    if _jaccard(cand_tokens, hp_tokens) >= 0.34:
                        # Link to historical clusters
                        hist_match = hp["orm_obj"]
                        curr_orm = db.query(PainPoint).filter(PainPoint.id == cand["id"]).first()
                        if curr_orm and hist_match.clusters:
                            for cluster in hist_match.clusters:
                                if curr_orm not in cluster.pain_points:
                                    cluster.pain_points.append(curr_orm)
                                    cluster.duplicate_count += 1
                            db.flush()
                        matched = True
                        matched_count += 1
                        break
                if not matched:
                    non_duplicate_candidates.append(cand)
            candidates = non_duplicate_candidates

        # Now, deduplicate remaining candidates amongst themselves
        deduped = deduplicate_pain_points(candidates, threshold, llm_config)
        
        # Commit the database changes
        db.commit()

        stats["deduplicate_unique"] = len(deduped)
        print(f"[DEDUPLICATE]  → {len(deduped)} unique clusters (merged {matched_count} into historical clusters)")
        return {"deduplicated_pain_points": deduped, "pipeline_stats": stats}
        
    except Exception as e:
        db.rollback()
        error_msg = f"Deduplicate node error: {e}"
        print(error_msg)
        # Fall back
        passthrough = [pp for pp in pain_points if pp.get("has_pain_point")]
        for pp in passthrough:
            pp.setdefault("duplicate_count", 1)
            pp.setdefault("duplicate_ids", [pp.get("id")])
        stats["deduplicate_unique"] = len(passthrough)
        return {"deduplicated_pain_points": passthrough, "error": error_msg, "pipeline_stats": stats}
    finally:
        db.close()
