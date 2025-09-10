import json
from pathlib import Path
from utils.llm import call_json

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "auditor_system.txt"

def audit(normalized: dict) -> dict:
    """
    Analyze a normalized input dictionary for inefficiencies using an LLM.
    Returns a dictionary with a 'findings' key containing up to 5 inefficiencies.

    Args:
        normalized (dict): The normalized input data to audit.

    Returns:
        dict: The LLM's response with identified inefficiencies under the 'findings' key.
    """
    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Failed to read system prompt: {e}"}

    try:
        jp = json.dumps(normalized, ensure_ascii=False)
        user_prompt = (
            "Analyze this normalized input and list at most 5 inefficiencies.\n"
            f"Input:\n{jp}\n"
            'Return JSON with key "findings".'
        )
        return call_json(system_prompt, user_prompt)
    except Exception as e:
        return {"error": f"Failed during LLM call or prompt construction: {e}"}
