from typing import Tuple, List, Dict, Any

def consistency_checks(input_d: Dict[str, Any], plan_d: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    flags: List[str] = []
    inp = input_d or {}
    plan = dict(plan_d or {})

    tariff = float(inp.get("tariff_LKR_per_kWh", 0) or 0)
    monthly_kwh = float(inp.get("monthly_kWh", 0) or 0)
    est_save_lkr = float(plan.get("estimated_monthly_savings_LKR", 0) or 0)
    est_pct = float(plan.get("estimated_savings_pct", 0) or 0)
    payback = plan.get("payback_months", None)

    current_bill = monthly_kwh * tariff

    if current_bill > 0 and est_save_lkr > current_bill:
        flags.append("savings_exceed_bill")
        plan["estimated_monthly_savings_LKR"] = current_bill

    if est_pct < 0 or est_pct > 100:
        flags.append("savings_pct_out_of_range")
        plan["estimated_savings_pct"] = max(0.0, min(100.0, est_pct))

    if isinstance(payback, (int, float)) and payback <= 0:
        flags.append("invalid_payback")
        plan["payback_months"] = None

    if plan.get("estimated_savings_pct", 0) and plan["estimated_savings_pct"] > 50:
        flags.append("needs_human_review")

    return plan, flags
