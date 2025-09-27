import os, json, re
from openai import OpenAI

_client = None

def _client_ok():
    global _client
    if _client is None:
        # simple client; per-request timeouts are set on create()
        _client = OpenAI()
    return _client

def _strip_markdown_fences(s: str) -> str:
    s = s.strip()
    # Remove leading and trailing code fences like ```json ... ```
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _normalize_quotes(s: str) -> str:
    # Normalize curly quotes to straight quotes to avoid parse errors inside strings
    return (
        s.replace("\u201c", '"').replace("\u201d", '"')  # left/right double
         .replace("\u2018", "'").replace("\u2019", "'")  # left/right single
    )

def _extract_balanced_json_object(s: str) -> str | None:
    """
    Extract the first balanced top-level JSON object {...} accounting for strings/escapes.
    """
    s = _strip_markdown_fences(_normalize_quotes(s))

    start = s.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
    return None

def _post_clean_json_text(t: str) -> str:
    # remove trailing commas before a } or ]
    t = re.sub(r",\s*([}\]])", r"\1", t)
    # replace non-JSON tokens with null
    t = re.sub(r"\bNaN\b|\bInfinity\b|\b-?Inf\b", "null", t)
    return t

def _coerce_and_load_json(raw: str):
    """
    Very tolerant loader:
    - extracts the first balanced {...} block
    - cleans trailing commas and odd tokens
    - then json.loads()
    """
    # try strict first
    try:
        return json.loads(raw)
    except Exception:
        pass

    # try balanced object extraction
    candidate = _extract_balanced_json_object(raw)
    if candidate is None:
        # as a last attempt, try trimming to first/last braces naively
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end + 1]
        else:
            raise

    candidate = _post_clean_json_text(candidate)
    return json.loads(candidate)

def call_json(system_prompt: str,
              user_prompt: str,
              model: str | None = None,
              temperature: float = 0.0,
              max_tokens: int = 400,
              timeout: int = 12):
    """
    Strict JSON response with small output cap and short timeout.
    Falls back to a tolerant JSON loader if the first parse fails.
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
        response_format={"type": "json_object"},  # ask server to enforce JSON
        timeout=timeout,
    )
    content = resp.choices[0].message.content or ""

    # First try strict load; fallback to tolerant load with balanced braces
    try:
        return json.loads(content)
    except Exception:
        try:
            return _coerce_and_load_json(content)
        except Exception as e:
            snippet = content[:600].replace("\n", "\\n")
            raise ValueError(f"Model returned non-JSON. Snippet: {snippet} ...") from e

def call_text(system_prompt: str,
              user_prompt: str,
              model: str | None = None,
              temperature: float = 0.0,
              max_tokens: int = 400,
              timeout: int = 12):
    """
    Plain text response with small output cap and short timeout.
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
    return resp.choices[0].message.content
