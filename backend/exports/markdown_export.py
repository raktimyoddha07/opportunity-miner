"""
Markdown exporter (AGENTS.md "Export Formats").

Layout:

    # Opportunity Report
    Generated: {date}

    ## {opportunity_title}
    Score: {score}
    ### Evidence
    - "{quote}" — r/{subreddit}
    ### Ideas
    ...

Pure serializer: takes the dataset from services/exports.gather_export_dataset.
"""
from datetime import datetime, timezone


def _index_evidence_by_cluster(evidence: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for pp in evidence:
        cid = pp.get("cluster_id")
        if cid:
            index.setdefault(cid, []).append(pp)
    return index


def _evidence_lines(evidence_for_cluster: list[dict]) -> list[str]:
    """Render quoted evidence bullets, deduplicated, capped to keep it readable."""
    lines: list[str] = []
    seen: set[str] = set()
    for pp in evidence_for_cluster:
        quote = (pp.get("quoted_evidence") or pp.get("summary") or "").strip()
        if not quote or quote in seen:
            continue
        seen.add(quote)
        doc = pp.get("source_document") or {}
        sub = (doc.get("metadata") or {}).get("subreddit", "")
        url = doc.get("url", "")
        suffix = f" — r/{sub}" if sub else ""
        if url:
            suffix += f" ({url})"
        lines.append(f'- "{quote[:280]}"{suffix}')
    return lines


def _idea_lines(ideas: list[dict]) -> list[str]:
    if not ideas:
        return ["_(no ideas generated)_"]
    return [
        f"- **{i.get('type', '').replace('_', ' ').title()}**: "
        f"{i.get('title', '')} — {i.get('description', '')}".rstrip(" —")
        for i in ideas
    ]


def export_markdown(dataset: dict) -> str:
    """
    Render the export dataset to a Markdown report string.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    evidence_by_cluster = _index_evidence_by_cluster(dataset.get("evidence", []))
    opportunities = dataset.get("opportunities", [])

    parts: list[str] = [
        "# Opportunity Report",
        f"Generated: {now}",
        "",
        f"_{len(opportunities)} validated opportunity(ies)._",
        "",
    ]

    for opp in opportunities:
        cluster_evidence = evidence_by_cluster.get(opp.get("cluster_id"), [])
        parts.append("---")
        parts.append("")
        parts.append(f"## {opp.get('title', 'Untitled opportunity')}")
        parts.append(f"- **Score:** {opp.get('score', 0)}")
        parts.append(f"- **Category:** {opp.get('category', 'uncategorized')}")
        parts.append(f"- **Confidence:** {opp.get('confidence', 0)}")
        if opp.get("summary"):
            parts.append(f"- **Summary:** {opp['summary']}")
        parts.append("")
        parts.append("### Evidence")
        ev_lines = _evidence_lines(cluster_evidence)
        parts.extend(ev_lines if ev_lines else ["_(no quotable evidence)_"])
        parts.append("")
        parts.append("### Ideas")
        parts.extend(_idea_lines(opp.get("ideas") or []))
        parts.append("")

    return "\n".join(parts)
