import os, json, re
from openai import OpenAI

from .json_tools import extract_json_block, try_json_loads

_client = None

def _client_ok():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

def _strip_markdown_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def call_text(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 1000,
    timeout: int | None = None,
    model: str | None = None,
) -> str:
    """
    Minimal chat call; returns message.content (string).
    """
    client = _client_ok()
    model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout=timeout,
    )
    content = resp.choices[0].message.content or ""
    return content

_JSON_REPAIR_SYSTEM = (
    "You are a strict JSON repair assistant. Output ONLY valid JSON that obeys the schema keys and types. "
    "No markdown, no comments."
)
_JSON_REPAIR_USER_TMPL = """The following was intended to be valid JSON, but it failed to parse.
Return a corrected JSON that preserves the same intent.

RAW:
```txt
{bad}
```"""

def _repair_json_with_model(raw: str, *, temperature: float = 0.0, max_tokens: int = 1000, timeout: int | None = None, model: str | None = None) -> dict:
    """
    Ask the model to repair malformed JSON. This function lives here (not in json_tools)
    to avoid circular imports.
    """
    candidate = extract_json_block(raw)
    ok, data = try_json_loads(candidate)
    if ok:
        return data

    repaired = call_text(
        system_prompt=_JSON_REPAIR_SYSTEM,
        user_prompt=_JSON_REPAIR_USER_TMPL.format(bad=raw),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        model=model,
    )
    repaired = extract_json_block(repaired)
    return json.loads(repaired)

def call_json(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1000,
    timeout: int | None = None,
    model: str | None = None,
):
    """
    Call the LLM for JSON output.
    - First attempt: parse the raw content directly
    - On failure: try to repair using a second LLM call
    """
    raw = call_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        model=model,
    )
    raw_clean = _strip_markdown_fences(raw)
    try:
        return json.loads(raw_clean)
    except Exception:
        return _repair_json_with_model(
            raw_clean,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            model=model,
        )