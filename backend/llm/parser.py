import json
import re

def parse_json_from_llm(output_text: str) -> dict | list:
    """
    Strips markdown JSON wrappers and parses string to dict/list.
    Includes fallback regex repair and key-value extraction for common LLM syntax flaws
    (such as missing colons, extra/missing commas, or unescaped characters).
    """
    if not output_text or not output_text.strip():
        raise ValueError("Empty output from LLM")

    # 1. Basic cleaning: remove markdown code blocks
    cleaned = output_text.replace("```json", "").replace("```", "").strip()

    # 2. Extract JSON payload between first { and last } or first [ and last ]
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)

    # Attempt standard parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback 1: Fix trailing commas before closing brackets/braces (e.g. `,"category": "x",}`)
    repaired = re.sub(r",\s*([\}\]])", r"\1", cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Fallback 2: Replace control characters and unescaped newlines within strings
    repaired_ctrl = re.sub(r"[\x00-\x1F\x7F]", " ", cleaned)
    repaired_ctrl = re.sub(r",\s*([\}\]])", r"\1", repaired_ctrl)
    try:
        return json.loads(repaired_ctrl)
    except json.JSONDecodeError:
        pass

    # Fallback 3: Regex key-value extractor when JSON syntax is severely corrupted (e.g. missing colon or quote)
    if cleaned.startswith("{"):
        extracted = {}
        known_keys = [
            "has_pain_point", "summary", "category", "emotion", "intensity", 
            "quoted_evidence", "confidence", "is_valid", "reasoning", "ideas"
        ]
        for key in known_keys:
            # Match "key" followed optionally by colon or spaces, then capture string/bool/number
            pattern = rf'"{key}"\s*:?\s*("(.*?)"|true|false|\d+)'
            m = re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL)
            if m:
                val_str = m.group(1).strip()
                if val_str.startswith('"') and val_str.endswith('"'):
                    extracted[key] = val_str[1:-1]
                elif val_str.lower() == "true":
                    extracted[key] = True
                elif val_str.lower() == "false":
                    extracted[key] = False
                elif val_str.isdigit():
                    extracted[key] = int(val_str)
                else:
                    extracted[key] = val_str
        if extracted:
            return extracted

    # If all fallbacks fail, raise original exception on cleaned text
    return json.loads(cleaned)
