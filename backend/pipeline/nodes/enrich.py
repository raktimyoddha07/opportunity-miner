"""
Enrich pipeline node — runs between clean and extract.

Implements:
  1. Urgency / willingness-to-pay keyword pre-scorer (extralogic Upgrade 2)
  2. spaCy entity extraction for competitor/tool names (extralogic Upgrade 3)

Contract:
  Input  key: cleaned_documents
  Output key: cleaned_documents  (enriched in-place — same key, no new node needed)
  Uses LLM: No

Documents that score urgency_score = 0 AND are shorter than MIN_URGENCY_LENGTH
characters are dropped here rather than wasted on the LLM. This significantly
cuts Ollama inference time for a single-subreddit run.
"""

from __future__ import annotations
from backend.pipeline.state import PipelineState

# ---------------------------------------------------------------------------
# Upgrade 2: Urgency / willingness-to-pay keyword scorer
# ---------------------------------------------------------------------------

URGENCY_KEYWORDS: list[tuple[str, int]] = [
    ("would pay",           3),
    ("paying for",          3),
    ("switched from",       2),
    ("anyone built",        2),
    ("wish someone would",  2),
    ("hours every week",    2),
    ("my whole team",       2),
    ("every single time",   2),
    ("can't believe",       1),
    ("cant believe",        1),
    ("so frustrating",      1),
    ("still no way to",     1),
    ("has anyone solved",   1),
    ("nobody has built",    2),
    ("why doesn't",         1),
    ("drives me crazy",     1),
    ("costing us",          2),
    ("losing hours",        2),
    ("waste of time",       1),
    ("manual process",      2),
    ("do it manually",      2),
    ("copy paste",          1),
    ("would love to pay",   3),
]

# Documents shorter than this AND with urgency_score==0 get skipped
MIN_URGENCY_LENGTH = 100


def compute_urgency_score(text: str) -> int:
    """Return a weighted sum of urgency/WTP keyword matches in text."""
    lower = text.lower()
    score = 0
    for phrase, weight in URGENCY_KEYWORDS:
        if phrase in lower:
            score += weight
    return score


# ---------------------------------------------------------------------------
# Upgrade 3: spaCy entity extraction
# ---------------------------------------------------------------------------

_nlp = None  # lazy singleton — loaded once on first use


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"[enrich] spaCy unavailable: {e}. Entity extraction disabled.")
            _nlp = False  # sentinel so we don't retry
    return _nlp if _nlp else None


def extract_entities(text: str) -> list[str]:
    """Return a deduplicated list of ORG/PRODUCT/GPE named entities from text."""
    nlp = _get_nlp()
    if nlp is None:
        return []
    try:
        doc = nlp(text[:5000])  # cap for speed — spaCy is linear but still
        entities = [
            ent.text.strip()
            for ent in doc.ents
            if ent.label_ in {"ORG", "PRODUCT", "GPE", "WORK_OF_ART"}
               and len(ent.text.strip()) > 1
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for e in entities:
            lower = e.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(e)
        return unique
    except Exception as exc:
        print(f"[enrich] entity extraction failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


def enrich_node(state: PipelineState) -> dict:
    """
    Enrich cleaned documents with urgency_score and named entities.
    Drops low-signal documents that would waste LLM inference time.

    Input:  cleaned_documents
    Output: cleaned_documents (enriched + filtered)
    """
    docs = state.get("cleaned_documents", [])
    enriched: list[dict] = []
    skipped = 0

    for doc in docs:
        content: str = doc.get("content", "") or ""

        # --- Upgrade 2: urgency scoring ---
        urgency = compute_urgency_score(content)

        # Drop very short, zero-urgency documents before hitting the LLM
        if urgency == 0 and len(content) < MIN_URGENCY_LENGTH:
            skipped += 1
            continue

        # --- Upgrade 3: entity extraction ---
        entities = extract_entities(content)

        # Merge back into the document dict
        updated = dict(doc)
        metadata = dict(updated.get("metadata") or {})
        metadata["urgency_score"] = urgency
        metadata["extracted_entities"] = entities
        updated["metadata"] = metadata

        enriched.append(updated)

    print(
        f"[enrich] {len(docs)} in → {len(enriched)} enriched "
        f"({skipped} low-signal dropped)"
    )
    return {"cleaned_documents": enriched}
