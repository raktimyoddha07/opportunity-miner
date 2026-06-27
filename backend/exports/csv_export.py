"""
CSV exporter (AGENTS.md "Export Formats").

Columns:
    opportunity, score, category, frequency, subreddit_count, top_quote, generated_idea

Pure serializer: takes the dataset produced by
services/exports.gather_export_dataset and returns CSV text. No DB access here.
"""
import csv
import io


CSV_COLUMNS = [
    "opportunity",
    "score",
    "category",
    "frequency",
    "subreddit_count",
    "top_quote",
    "generated_idea",
]


def _index_evidence_by_cluster(evidence: list[dict]) -> dict[str, list[dict]]:
    """Group evidence pain points by their cluster_id."""
    index: dict[str, list[dict]] = {}
    for pp in evidence:
        cid = pp.get("cluster_id")
        if cid:
            index.setdefault(cid, []).append(pp)
    return index


def _top_quote(opportunity: dict, evidence_for_cluster: list[dict]) -> str:
    """Highest-confidence quoted evidence backing this opportunity."""
    if evidence_for_cluster:
        best = max(
            evidence_for_cluster,
            key=lambda p: (p.get("confidence") or 0, p.get("intensity") or 0),
        )
        if best.get("quoted_evidence"):
            return best["quoted_evidence"]
    return opportunity.get("summary") or ""


def _subreddit_count(evidence_for_cluster: list[dict]) -> int:
    subs = set()
    for pp in evidence_for_cluster:
        doc = pp.get("source_document") or {}
        sub = (doc.get("metadata") or {}).get("subreddit")
        if sub:
            subs.add(sub)
    return len(subs)


def _first_idea(opportunity: dict) -> str:
    ideas = opportunity.get("ideas") or []
    if not ideas:
        return ""
    first = ideas[0]
    label = first.get("type", "")
    title = first.get("title", "")
    return f"{label}: {title}" if label and title else (title or label)


def export_csv(dataset: dict) -> str:
    """
    Render the export dataset to CSV text.

    `dataset` shape: { opportunities, clusters, evidence, ideas }
    (see services/exports.gather_export_dataset)
    """
    evidence_by_cluster = _index_evidence_by_cluster(dataset.get("evidence", []))

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)

    for opp in dataset.get("opportunities", []):
        cluster_evidence = evidence_by_cluster.get(opp.get("cluster_id"), [])
        writer.writerow([
            opp.get("title", ""),
            opp.get("score", 0),
            opp.get("category", ""),
            opp.get("frequency", 0),
            _subreddit_count(cluster_evidence),
            _top_quote(opp, cluster_evidence),
            _first_idea(opp),
        ])

    return buf.getvalue()
