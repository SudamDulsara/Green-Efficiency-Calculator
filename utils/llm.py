from __future__ import annotations
import json
import os
import re
from typing import Any, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_CLIENT: Optional["OpenAI"] = None


def _client() -> "OpenAI":
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Add `openai>=1.50.0` to requirements.txt")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env")
    _CLIENT = OpenAI(api_key=api_key)
    return _CLIENT


def _model_name() -> str:
    return os.getenv("MODEL_NAME", "gpt-4o-mini")


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$", re.IGNORECASE)


def _strip_fences(s: str) -> str:
    m = _FENCE_RE.match(s)
    return m.group(1) if m else s


def _json_repair(s: str) -> str:
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first : last + 1]
    return s


def call_json(system_text: str, user_content: Any) -> Dict[str, Any]:

    try:
        client = _client()
        model = _model_name()

        msg = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
            ],
            temperature=0.2,
        )

        text = (msg.choices[0].message.content or "").strip()
        payload = text

        payload = _strip_fences(payload)
        try:
            return json.loads(payload)
        except Exception:
            repaired = _json_repair(payload)
            return json.loads(repaired)
    except Exception:
        return {}
