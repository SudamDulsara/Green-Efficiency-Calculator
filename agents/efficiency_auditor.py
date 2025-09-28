import json
from pathlib import Path
from utils.llm import call_json

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "auditor_system.txt"

def _read(p: Path) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def audit(normalized: dict, max_findings: int = 5) -> dict:
    """
    Analyze a normalized input dictionary for inefficiencies using an LLM.
    Always returns a dict with 'findings': list.
    """
    system_prompt = _read(PROMPT_PATH)
    user_prompt = (
        "Normalized input JSON:\n" + json.dumps(normalized, ensure_ascii=False)
        + f"\n\nConstraints:\n- Return at most {max_findings} findings.\n"
    )

    try:
        out = call_json(system_prompt, user_prompt)
        findings = out.get("findings", [])
        if not isinstance(findings, list):
            findings = []
    except Exception:
        findings = []

    if not findings:
        findings = [{
            "area": "other",
            "issue": "insufficient device details",
            "severity": "low",
            "reason": "No AC/lighting specifics given; a quick walk-through can reveal easy, low-cost wins."
        }]

    return {"findings": findings[:max_findings]}
