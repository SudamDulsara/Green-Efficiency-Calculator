from __future__ import annotations

from typing import Dict, Any, List, Tuple
from math import isfinite


def _num(x, default=0.0) -> float:
    try:
        v = float(x)
        return v if isfinite(v) else default
    except Exception:
        return default


_DISR = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _disruption_ok(action_level: str | None, max_level: str | None) -> bool:
    a = _DISR.get(str(action_level or "medium").lower(), 2)
    m = _DISR.get(str(max_level or "medium").lower(), 2)
    return a <= m


def _est_kwh_saved(action: Dict[str, Any], baseline_kwh: float) -> float:
    if action.get("kwh_saved_per_month") is not None:
        return max(_num(action.get("kwh_saved_per_month"), 0.0), 0.0)
    pct = max(min(_num(action.get("pct_kwh_reduction_min"), 0.0), 100.0), 0.0)
    return baseline_kwh * (pct / 100.0)


def _monthly_savings_LKR(action: Dict[str, Any], baseline_kwh: float, tariff: float) -> float:
    return _est_kwh_saved(action, baseline_kwh) * max(tariff, 0.0)


def _payback_months(action: Dict[str, Any], baseline_kwh: float, tariff: float) -> float | None:
    if action.get("payback_months") is not None and _num(action["payback_months"], -1) >= 0:
        return float(action["payback_months"])
    capex = max(_num(action.get("est_cost"), 0.0), 0.0)
    monthly = _monthly_savings_LKR(action, baseline_kwh, tariff)
    return (capex / monthly) if monthly > 0 else None


def _value_per_lkr(action: Dict[str, Any], baseline_kwh: float) -> float:
    capex = max(_num(action.get("est_cost"), 0.0), 0.0)
    kwh = _est_kwh_saved(action, baseline_kwh)
    if capex <= 0:
        return 1e12 if kwh > 0 else 0.0
    return kwh / capex


def enforce_policy(
    recommendations: Dict[str, Any],
    policy: Dict[str, Any] | None,
    baseline_kwh: float,
    tariff_LKR_per_kWh: float,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Deterministically enforce:
      - max disruption
      - payback threshold
      - total budget (greedy best-subset by kWh/LKR)
    Returns (filtered_recommendations_obj, policy_report)
    """
    recs = list(recommendations.get("recommendations") or [])
    recs = [r for r in recs if isinstance(r, dict)]
    report: Dict[str, Any] = {"notes": [], "unmet_constraints": []}

    if not policy:
        return {"recommendations": recs}, report

    if policy.get("max_disruption"):
        before = len(recs)
        recs = [r for r in recs if _disruption_ok(r.get("disruption"), policy.get("max_disruption"))]
        if len(recs) < before:
            report["notes"].append("Dropped actions exceeding max disruption.")

    if policy.get("payback_threshold_months") is not None:
        thr = max(int(policy["payback_threshold_months"]), 0)
        kept, dropped = [], 0
        for a in recs:
            pb = _payback_months(a, baseline_kwh, tariff_LKR_per_kWh)
            if pb is None:
                if _num(a.get("est_cost"), 0.0) <= 5000:
                    a = dict(a)
                    a["payback_months"] = None
                    kept.append(a)
                else:
                    dropped += 1
            elif pb <= thr:
                a = dict(a)
                a["payback_months"] = pb
                kept.append(a)
            else:
                dropped += 1
        if dropped:
            report["notes"].append(f"Filtered {dropped} actions by payback ≤ {thr} months.")
        recs = kept

    if policy.get("target_budget_LKR") is not None:
        budget = max(float(policy["target_budget_LKR"]), 0.0)
        ranked = sorted(recs, key=lambda a: _value_per_lkr(a, baseline_kwh), reverse=True)
        chosen, spent = [], 0.0
        for a in ranked:
            capex = max(_num(a.get("est_cost"), 0.0), 0.0)
            if spent + capex <= budget:
                chosen.append(a)
                spent += capex
        recs = chosen
        report["notes"].append(
            f"Applied budget cap. Spent ~{round(spent, 2)} / {round(budget, 2)} LKR."
        )

    return {"recommendations": recs}, report
