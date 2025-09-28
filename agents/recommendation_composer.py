import json
from pathlib import Path

from utils.llm import call_json
from utils.guardrails import clamp_money

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

# def _post_checks(recs: dict) -> dict:
#     for r in recs.get("recommendations", []):
#         r["estimated_monthly_savings_LKR"] = clamp_money(r.get("estimated_monthly_savings_LKR", 0))
#         # flag extreme claims
#         if r.get("estimated_savings_pct", 0) > 50:
#             r["flag"] = "needs_human_review"
#         # require payback positive
#         if r.get("payback_months", 0) < 0:
#             r["payback_months"] = None
#             r["flag"] = "invalid_payback"
#     return recs

