import json
from typing import Tuple

def extract_json_block(text: str) -> str:
    """
    Try to extract the first top-level {...} JSON object from text.
    If none found, return stripped text as-is.
    """
    if not isinstance(text, str):
        return text
    stack = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if stack == 0:
                start = i
            stack += 1
        elif ch == '}':
            if stack > 0:
                stack -= 1
                if stack == 0 and start is not None:
                    return text[start:i+1]
    return text.strip()

def try_json_loads(s: str) -> Tuple[bool, dict | None]:
    try:
        return True, json.loads(s)
    except Exception:
        return False, None
