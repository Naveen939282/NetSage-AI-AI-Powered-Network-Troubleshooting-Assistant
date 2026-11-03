from __future__ import annotations
import re
from typing import Any
from ai.schemas import AIDiagnosis


def _extract_json_text(s: str) -> str | None:
    if not s or not isinstance(s, str):
        return None
    # look for ```json ... ``` or ``` ... ``` fenced blocks
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", s, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"```\s*(\{[\s\S]*?\})\s*```", s)
    if m:
        return m.group(1)
    # fallback: find first balanced JSON object starting with '{'
    idx = s.find("{")
    if idx == -1:
        return None
    depth = 0
    for i in range(idx, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[idx:i+1]
    return None


def parse_ai_response(raw: Any) -> AIDiagnosis:
    """Take raw provider response (str or dict), extract JSON, and validate with Pydantic.

    Raises ValueError on invalid or missing required fields.
    """
    if isinstance(raw, AIDiagnosis):
        return raw
    if isinstance(raw, dict):
        return AIDiagnosis.model_validate(raw)
    if not isinstance(raw, str):
        raise ValueError("Unsupported AI response type")

    jtext = _extract_json_text(raw)
    if not jtext:
        # Try to parse raw as JSON-ish
        jtext = raw.strip()
    try:
        import json

        payload = json.loads(jtext)
    except Exception as e:
        raise ValueError(f"Failed to extract/parse JSON from AI response: {e}")

    return AIDiagnosis.model_validate(payload)
