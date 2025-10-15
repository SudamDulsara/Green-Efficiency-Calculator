from __future__ import annotations
from typing import Any, Dict, Tuple

def _get_num(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if v != v:
            return default
        return v
    except Exception:
        return default

def _get_str(x: Any, default: str = "") -> str:
    return str(x) if isinstance(x, str) else default

def _disr_rank(label: str) -> int:
    table = {"none": 0, "low": 1, "medium": 2, "high": 3}
    return table.get(label.lower(), 2)

def _collect_disruption(recommendations: Dict[str, Any]) -> int:
    recs = []
    if hasattr(recommendations, "recommendations"):
        recs = getattr(recommendations, "recommendations")
    elif isinstance(recommendations, dict):
        recs = recommendations.get("recommendations", [])
    max_rank = 0
    for r in recs:
        d = r.get("disruption") if isinstance(r, dict) else getattr(r, "disruption", "medium")
        max_rank = max(max_rank, _disr_rank(_get_str(d, "medium")))
    return max_rank

def check_against_criteria(result: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Enforces (if provided):
      - max_budget_LKR  (capex)
      - payback_threshold_months (blended payback)
      - require_data_complete (monthly_kWh & tariff)
      - co2_reduction_goal_pct (kWh saved relative to baseline)
      - max_disruption (none/low/medium/high)
    Returns (ok, reason, patch_for_retry)
    """
    reasons = []
    patch: Dict[str, Any] = {}

    normalized = result.get("normalized")
    impact_plan = result.get("impact_plan") or result.get("plan")
    recommendations = result.get("recommendations")

    if hasattr(normalized, "model_dump"):
        n = normalized.model_dump()
    else:
        n = normalized or {}

    if hasattr(impact_plan, "model_dump"):
        p = impact_plan.model_dump()
    else:
        p = impact_plan or {}

    totals = (p or {}).get("totals", {})
    total_capex = _get_num(totals.get("total_capex_LKR"))
    blended_payback = totals.get("blended_payback_months", None)
    blended_payback_num = None if blended_payback is None else _get_num(blended_payback, 0.0)
    total_kwh_saved = _get_num(totals.get("total_monthly_kwh_saved"))

    baseline_kwh = _get_num(n.get("monthly_kWh"))
    tariff = _get_num(n.get("tariff_LKR_per_kWh"))

    ok = True

    if criteria.get("require_data_complete"):
        missing = []
        if baseline_kwh <= 0:
            missing.append("monthly_kWh")
        if tariff <= 0:
            missing.append("tariff_LKR_per_kWh")
        if missing:
            ok = False
            reasons.append(f"data incomplete: missing {', '.join(missing)}")

    if criteria.get("max_budget_LKR") is not None:
        max_budget = _get_num(criteria.get("max_budget_LKR"))
        if total_capex > max_budget:
            ok = False
            reasons.append(f"over budget: capex {total_capex:.0f} > {max_budget:.0f} LKR")
            patch.setdefault("policy", {})["target_budget_LKR"] = max_budget

    if criteria.get("payback_threshold_months") is not None and blended_payback_num is not None:
        thr = _get_num(criteria.get("payback_threshold_months"))
        if blended_payback_num > thr:
            ok = False
            reasons.append(f"payback too long: {blended_payback_num:.1f} > {thr:.1f} months")
            patch.setdefault("policy", {})["payback_threshold_months"] = thr

    if criteria.get("co2_reduction_goal_pct") is not None and baseline_kwh > 0:
        goal_pct = _get_num(criteria.get("co2_reduction_goal_pct"))
        achieved_pct = (total_kwh_saved / baseline_kwh) * 100.0 if baseline_kwh > 0 else 0.0
        if achieved_pct + 1e-9 < goal_pct:
            ok = False
            reasons.append(f"CO₂/kWh reduction shortfall: {achieved_pct:.1f}% < {goal_pct:.1f}%")
            patch.setdefault("policy", {})["co2_reduction_goal_pct"] = goal_pct

    if criteria.get("max_disruption") is not None:
        required_cap = str(criteria.get("max_disruption")).lower()
        max_rank_seen = _collect_disruption(recommendations)
        rank_cap = _disr_rank(required_cap)
        if max_rank_seen > rank_cap:
            ok = False
            reasons.append(f"disruption too high (max seen rank {max_rank_seen} > cap {rank_cap})")
            patch.setdefault("policy", {})["max_disruption"] = required_cap

    reason = "OK" if ok else "; ".join(reasons) or "failed criteria"
    return ok, reason, patch
