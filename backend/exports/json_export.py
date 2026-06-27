"""
JSON exporter (AGENTS.md "Export Formats").

Full nested structure:
    { opportunities: [], clusters: [], evidence: [], ideas: [] }

Pure serializer: the dataset from services/exports.gather_export_dataset is
already JSON-safe (UUIDs -> str, datetimes -> isoformat), so this just wraps
and pretty-prints it.
"""
import json


def export_json(dataset: dict) -> str:
    """
    Render the export dataset as a pretty JSON string.

    `dataset` shape: { opportunities, clusters, evidence, ideas }
    """
    payload = {
        "opportunities": dataset.get("opportunities", []),
        "clusters": dataset.get("clusters", []),
        "evidence": dataset.get("evidence", []),
        "ideas": dataset.get("ideas", []),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)
