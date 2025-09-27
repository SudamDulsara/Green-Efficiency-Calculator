import math
from pathlib import Path
from utils.guardrails import clamp_money
from utils.llm import call_text

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "impact_system.txt"

def _safe_pct(a):
    try:
        return float(a)
    except Exception:
        return 0.0

def estimate_impact(normalized: dict, recs: dict) -> dict:
    monthly_kwh = float(normalized.get("monthly_kWh", 0.0))
    tariff = float(normalized.get("tariff_LKR_per_kWh", 0.0))
    items = []

    for r in recs.get("recommendations", []):
        pmin = max(0.0, _safe_pct(r.get("pct_kwh_reduction_min", 0.0)))
        pmax = max(pmin, _safe_pct(r.get("pct_kwh_reduction_max", pmin)))
        # conservative midpoint
        pct = (pmin + pmax) / 2.0
        kwh_saved = monthly_kwh * (pct / 100.0)
        lkr_saved = kwh_saved * tariff
        est_cost = clamp_money(r.get("est_cost", 0.0))
        payback = (est_cost / lkr_saved) if lkr_saved > 0 else math.inf

        items.append({
            "action": r.get("action",""),
            "steps": r.get("steps", []),
            "pct_kwh_reduction_used": round(pct, 2),
            "kWh_saved_per_month": round(kwh_saved, 2),
            "LKR_saved_per_month": round(lkr_saved, 2),
            "est_cost": round(est_cost, 2),
            "payback_months": round(payback, 1) if math.isfinite(payback) else None,
            "notes": r.get("notes","")
        })

    # Sort by payback (fastest first). Items without payback go last.
    items.sort(key=lambda x: (float('inf') if x["payback_months"] is None else x["payback_months"]))

    quick_wins = items[:3]
    totals = {
        "kWh_saved_per_month": round(sum(x["kWh_saved_per_month"] for x in items), 2),
        "LKR_saved_per_month": round(sum(x["LKR_saved_per_month"] for x in items), 2),
    }

    # Generate short action plan text via LLM
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    context = {
        "input": {
            "floor_area_m2": normalized.get("floor_area_m2"),
            "tariff_LKR_per_kWh": tariff,
            "monthly_kWh": monthly_kwh
        },
        "actions": items,
        "totals": totals
    }
    user_prompt = (
        "Write a concise action plan with 3 sections: Quick Wins, Next Steps, Estimated Impact.\n"
        "Prioritize clarity and numbers.\n"
        f"{context}"
    )
    plan_text = call_text(system_prompt, user_prompt)

    return {
        "quick_wins": quick_wins,
        "all_actions": items,
        "totals": totals,
        "plan_text": plan_text
    }
