import json
from pathlib import Path
from utils.llm import call_json

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "auditor_system.txt"

def audit(normalized: dict) -> dict:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    jp = json.dumps(normalized, ensure_ascii=False)
    user_prompt = (
        "Analyze this normalized input and list at most 5 inefficiencies.\n"
        f"Input:\n{jp}\n"
        'Return JSON with key "findings".'
    )
    return call_json(system_prompt, user_prompt)
