from utils.guardrails import clamp_money

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _render_plan_text(normalized: dict, items: list, totals: dict) -> str:
    quick = sorted(items, key=lambda a: _safe_float(a.get("est_cost"), 0.0))[:3]

    lines = []
    lines.append("# Action Plan")
    lines.append("## Quick Wins")
    if quick:
        for a in quick:
            kwh = _safe_float(a.get("kWh_saved_per_month"), 0)
            lkr = _safe_float(a.get("LKR_saved_per_month"), 0)
            steps = a.get("steps") or []
            lines.append(f"- **{a.get('action','(action)')}**: save ~{kwh:.0f} kWh/mo (~LKR {lkr:.0f}/mo).")
            if steps:
                lines.append("  - Steps: " + "; ".join(steps))
    else:
        lines.append("- Review usage patterns; no low-cost items detected.")

    lines.append("## Next Steps")
    for a in items:
        if a in quick:
            continue
        est_cost = _safe_float(a.get("est_cost"), 0)
        lines.append(f"- **{a.get('action','(action)')}** (est. cost LKR {est_cost:.0f})")

    lines.append("## Estimated Impact")
    lines.append(f"- Total: ~{totals['kWh_saved_per_month']:.0f} kWh/mo "
                 f"(~LKR {totals['LKR_saved_per_month']:.0f}/mo)")
    return "\n".join(lines)

def estimate_impact(normalized: dict, recs: dict) -> dict:
    
    """
    Convert recommendation % ranges to kWh and LKR savings and render a concise plan locally.
    Expected `recs` shape:
      {"recommendations":[
        {"action":"...", "steps":[...],
         "pct_kwh_reduction_min": number, "pct_kwh_reduction_max": number,
         "est_cost": number, "notes":"..."}
      ]}
    """
    monthly_kwh = _safe_float(normalized.get("monthly_kWh"), 0.0)
    tariff = _safe_float(normalized.get("tariff_LKR_per_kWh"), 0.0)
    rec_items = (recs or {}).get("recommendations") or []

    items = []
    for r in rec_items:
        pct_min = _safe_float(r.get("pct_kwh_reduction_min", r.get("pct_kwh_reduction", 0.0)), 0.0)
        pct_min = max(0.0, min(100.0, pct_min))
        kwh_saved = monthly_kwh * (pct_min / 100.0)
        lkr_saved = kwh_saved * tariff

        item = {
            "action": r.get("action", "(action)"),
            "steps": r.get("steps") or [],
            "kWh_saved_per_month": kwh_saved,
            "LKR_saved_per_month": lkr_saved,
            "kwh_saved_per_month": kwh_saved,
            "lkr_saved_per_month": lkr_saved,
            "est_cost": clamp_money(r.get("est_cost", 0.0)),
            "notes": r.get("notes", ""),
        }
        items.append(item)

    quick_wins = sorted(items, key=lambda a: _safe_float(a.get("est_cost"), 0.0))[:3]

    totals_kwh = sum(_safe_float(a.get("kWh_saved_per_month"), 0.0) for a in items)
    totals_lkr = sum(_safe_float(a.get("LKR_saved_per_month"), 0.0) for a in items)

    totals = {
        "kWh_saved_per_month": totals_kwh,
        "LKR_saved_per_month": totals_lkr,
        "kwh_saved_per_month": totals_kwh,
        "lkr_saved_per_month": totals_lkr,
    }

    plan_text = _render_plan_text(normalized, items, totals)

    return {
        "quick_wins": quick_wins,
        "all_actions": items,
        "totals": totals,
        "plan_text": plan_text,
    }
