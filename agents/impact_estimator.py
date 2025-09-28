from utils.guardrails import clamp_money

def _fnum(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def estimate_impact(normalized: dict, recs: dict) -> dict:
    """
    Aggregate recommendation savings into a simple plan.
    - If recs empty, return a minimal plan (0 totals, but still structured).
    - If only percentages present, derive LKR from bill (monthly_kWh * tariff).
    """
    recommendations = recs.get("recommendations", []) if isinstance(recs, dict) else []
    monthly_kwh = _fnum(normalized.get("monthly_kWh", 0))
    tariff = _fnum(normalized.get("tariff_LKR_per_kWh", 0))
    bill_lkr = monthly_kwh * tariff

    if not recommendations:
        return {
            "quick_wins": [],
            "all_actions": [],
            "totals": {"kWh_saved_per_month": 0.0, "LKR_saved_per_month": 0.0},
            "plan_text": "# Action Plan\nNo actionable items beyond general review."
        }

    lkr_saved = 0.0
    for r in recommendations:
        s_lkr = r.get("estimated_monthly_savings_LKR", None)
        s_pct = r.get("estimated_savings_pct", None)
        if isinstance(s_lkr, (int, float)):
            lkr_saved += float(s_lkr)
        elif isinstance(s_pct, (int, float)) and bill_lkr > 0:
            lkr_saved += (float(s_pct) / 100.0) * bill_lkr

    lkr_saved = clamp_money(lkr_saved)
    if bill_lkr > 0 and lkr_saved > bill_lkr:
        lkr_saved = bill_lkr

    kwh_saved = (lkr_saved / tariff) if tariff > 0 else 0.0

    quick = recommendations[:3]
    plan_text = (
        "# Action Plan\n"
        "## Quick Wins\n"
        + "".join([f"- {r.get('action','(action)')}\n" for r in quick])
        + "## Estimated Impact\n"
        + f"- Total: ~{round(kwh_saved,2)} kWh/mo (~LKR {round(lkr_saved,2)}/mo)"
    )

    return {
        "quick_wins": quick,
        "all_actions": recommendations,
        "totals": {
            "kWh_saved_per_month": round(kwh_saved, 2),
            "LKR_saved_per_month": round(lkr_saved, 2),
        },
        "plan_text": plan_text,
    }
