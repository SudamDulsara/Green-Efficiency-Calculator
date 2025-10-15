from __future__ import annotations
from typing import List, Dict, Any, Tuple
from math import isfinite

from utils.models import NormalizedInput, Recommendations, Recommendation

_DISR_ORDER = ["none", "low", "medium", "high"]
_IDX = {v: i for i, v in enumerate(_DISR_ORDER)}


def _disruption_ok(level: str | None, max_level: str | None) -> bool:
    lvl = (level or "medium").strip().lower()
    mx = (max_level or "medium").strip().lower()
    return _IDX.get(lvl, 2) <= _IDX.get(mx, 2)


def _num(x, default=0.0) -> float:
    try:
        v = float(x)
        return v if isfinite(v) else default
    except Exception:
        return default


def _est_kwh_saved_per_month(a: Dict[str, Any], baseline_kwh: float) -> float:
    if a.get("kwh_saved_per_month") is not None:
        return max(_num(a.get("kwh_saved_per_month"), 0.0), 0.0)
    pct_min = max(_num(a.get("pct_kwh_reduction_min"), 0.0), 0.0)
    pct_min = min(pct_min, 100.0)
    return baseline_kwh * (pct_min / 100.0)


def _monthly_savings_LKR(a: Dict[str, Any], baseline_kwh: float, tariff: float) -> float:
    kwh = _est_kwh_saved_per_month(a, baseline_kwh)
    return max(kwh * max(tariff, 0.0), 0.0)


def _payback_months(a: Dict[str, Any], baseline_kwh: float, tariff: float) -> float | None:
    if a.get("payback_months") is not None:
        p = _num(a.get("payback_months"), -1.0)
        return p if p >= 0 else None
    capex = _num(a.get("est_cost"), 0.0)
    monthly = _monthly_savings_LKR(a, baseline_kwh, tariff)
    if monthly > 0:
        return capex / monthly
    return None


def _to_dict(r: Recommendation) -> Dict[str, Any]:
    return r.model_dump()


def _to_model(d: Dict[str, Any]) -> Recommendation:
    return Recommendation(**{
        "action": d.get("action"),
        "steps": d.get("steps") or [],
        "pct_kwh_reduction_min": d.get("pct_kwh_reduction_min", 0.0),
        "pct_kwh_reduction_max": d.get("pct_kwh_reduction_max", 0.0),
        "est_cost": d.get("est_cost", 0.0),
        "notes": d.get("notes") or "",
        "disruption": (d.get("disruption") or "medium"),
        "kwh_saved_per_month": d.get("kwh_saved_per_month"),
        "payback_months": d.get("payback_months"),
    })


def _value_per_LKR(a: Dict[str, Any], baseline_kwh: float) -> float:
    capex = max(_num(a.get("est_cost"), 0.0), 0.0)
    kwh = _est_kwh_saved_per_month(a, baseline_kwh)
    if capex <= 0:
        return 1e12 if kwh > 0 else 0.0
    return kwh / capex


def apply_policy(recs: Recommendations, normalized: NormalizedInput) -> Tuple[Recommendations, Dict[str, Any]]:
    report: Dict[str, Any] = {"notes": [], "unmet_constraints": []}
    policy = normalized.policy
    base_kwh = max(normalized.monthly_kWh or 0.0, 0.0)
    tariff = max(normalized.tariff_LKR_per_kWh or 0.0, 0.0)

    items: List[Dict[str, Any]] = [_to_dict(r) for r in (recs.recommendations or [])]

    if policy and policy.max_disruption:
        before = len(items)
        items = [a for a in items if _disruption_ok(a.get("disruption"), policy.max_disruption)]
        if len(items) < before:
            report["notes"].append("Dropped actions exceeding max disruption.")

    if policy and policy.payback_threshold_months is not None:
        thr = max(int(policy.payback_threshold_months), 0)
        kept = []
        dropped = 0
        for a in items:
            pb = _payback_months(a, base_kwh, tariff)
            a["payback_months"] = pb
            if pb is None:
                if _num(a.get("est_cost"), 0.0) <= 5000:
                    kept.append(a)
                else:
                    dropped += 1
            else:
                if pb <= thr:
                    kept.append(a)
                else:
                    dropped += 1
        if dropped:
            report["notes"].append(f"Filtered {dropped} actions by payback threshold (≤ {thr} months).")
        items = kept

    if policy and policy.target_budget_LKR is not None:
        budget = max(float(policy.target_budget_LKR), 0.0)
        ranked = sorted(items, key=lambda a: _value_per_LKR(a, base_kwh), reverse=True)
        chosen: List[Dict[str, Any]] = []
        spent = 0.0
        for a in ranked:
            capex = max(_num(a.get("est_cost"), 0.0), 0.0)
            if spent + capex <= budget:
                chosen.append(a)
                spent += capex
        items = chosen
        report["notes"].append(f"Applied budget cap. Spent LKR ~{round(spent, 2)} of {round(budget, 2)}.")

    out_models = [_to_model(a) for a in items]
    out = Recommendations(recommendations=out_models, policy_report=report)
    return out, report
