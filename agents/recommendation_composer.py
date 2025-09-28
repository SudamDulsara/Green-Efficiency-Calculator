import json
from pathlib import Path
from utils.llm import call_json

# Paths to prompt files (relative to project root)
PROMPT_SYS = Path(__file__).resolve().parent.parent / "prompts" / "rec_system.txt"
PROMPT_USER = Path(__file__).resolve().parent.parent / "prompts" / "rec_user.txt"

def _read(p: Path) -> str:
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def _fallback_recs(normalized: dict) -> list:
    """Conservative baseline actions that make sense for most homes."""
    def fnum(x, default=0.0):
        try:
            return float(x)
        except Exception:
            return default

    monthly_kwh = fnum(normalized.get("monthly_kWh", 0))
    tariff = fnum(normalized.get("tariff_LKR_per_kWh", 0))
    bill = monthly_kwh * tariff

    recs = [
        {
            "action": "Switch off lights in unoccupied rooms; maximize daylight use",
            "area": "lighting",
            "estimated_savings_pct": 2.0,
            "estimated_monthly_savings_LKR": round(0.02 * bill, 2) if bill > 0 else 0.0,
            "capex_LKR": 0.0,
            "payback_months": None,
            "why": "Behavioral, zero-cost action applicable with limited device info."
        },
        {
            "action": "Unplug/disable standby loads (TV, routers, chargers) overnight",
            "area": "standby",
            "estimated_savings_pct": 1.5,
            "estimated_monthly_savings_LKR": round(0.015 * bill, 2) if bill > 0 else 0.0,
            "capex_LKR": 0.0,
            "payback_months": None,
            "why": "Standby draws are common and reduceable without cost."
        },
        {
            "action": "If using AC, set to 25–26°C and limit runtime to occupied periods",
            "area": "AC",
            "estimated_savings_pct": 3.0,
            "estimated_monthly_savings_LKR": round(0.03 * bill, 2) if bill > 0 else 0.0,
            "capex_LKR": 0.0,
            "payback_months": None,
            "why": "Temperature discipline typically reduces cooling energy."
        },
    ]
    return recs

def compose_recs(normalized: dict, findings: dict) -> dict:
    """
    Compose recommendations from LLM; if it fails or returns empty, use fallbacks.
    Always returns {"recommendations":[...]}.
    """
    try:
        system_prompt = _read(PROMPT_SYS)
        user_prompt = _read(PROMPT_USER)
        user_prompt = user_prompt.replace("{{normalized_json}}", json.dumps(normalized, ensure_ascii=False))
        user_prompt = user_prompt.replace("{{findings_json}}", json.dumps(findings, ensure_ascii=False))

        out = call_json(system_prompt, user_prompt)
        recs = out.get("recommendations", [])
        if not isinstance(recs, list):
            recs = []
    except Exception:
        recs = []

    if not recs:
        recs = _fallback_recs(normalized)

    return {"recommendations": recs[:5]}
