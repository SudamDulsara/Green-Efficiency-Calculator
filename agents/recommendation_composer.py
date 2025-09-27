import json
from pathlib import Path
from utils.llm import call_json

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "composer_system.txt"

def compose_recs(normalized: dict, findings: dict) -> dict:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    inp = {"normalized": normalized, "findings": findings}
    user_prompt = (
        "Create up to 5 practical actions from these findings and context. "
        "Prefer low-cost measures first.\n\n"
        "STRICTION:\n"
        "- OUTPUT ONLY VALID JSON. No markdown, no preface, no trailing commas.\n"
        '- Return exactly this shape: {"recommendations":[{"action":"...", "steps":["..."], '
        '"pct_kwh_reduction_min": number, "pct_kwh_reduction_max": number, "est_cost": number, "notes": ""}]}\n'
        "- Use integers for percentage fields. If unsure, choose conservative single digits.\n"
        "- Keep strings short and avoid special quotes.\n\n"
        f"INPUT:\n{json.dumps(inp, ensure_ascii=False)}"
    )

    return call_json(system_prompt, user_prompt)
