from __future__ import annotations
from typing import Dict, Any, List
import os

from utils.models import NormalizedInput, AuditResult, Recommendations, Recommendation
from utils.llm import call_json
from utils.constraints import apply_policy

def _fmt(v: Any, default_str: str) -> str:
    if v is None:
        return default_str
    try:
        if isinstance(v, (int,)) or (isinstance(v, float) and float(v).is_integer()):
            return str(int(v))
        return str(float(v))
    except Exception:
        return default_str


def _build_system_prompt(policy: Dict[str, Any] | None) -> str:
    BUDGET = "unbounded"
    PAYBACK = "unbounded"
    CO2_GOAL = "none"
    MAX_DISRUPTION = "medium"
    if policy:
        if policy.get("target_budget_LKR") is not None:
            BUDGET = str(int(policy.get("target_budget_LKR"))) if float(policy.get("target_budget_LKR")).is_integer() else str(policy.get("target_budget_LKR"))
        if policy.get("payback_threshold_months") is not None:
            PAYBACK = str(int(policy.get("payback_threshold_months")))
        if policy.get("co2_reduction_goal_pct") is not None:
            CO2_GOAL = str(policy.get("co2_reduction_goal_pct"))
        if policy.get("max_disruption"):
            MAX_DISRUPTION = str(policy.get("max_disruption")).lower().strip()

    sys_tmpl_path = os.path.join("prompts", "composer_system.txt")
    sys_tmpl = None
    try:
        with open(sys_tmpl_path, "r", encoding="utf-8") as f:
            sys_tmpl = f.read()
    except Exception:
        sys_tmpl = (
            'Return ONLY JSON: {"recommendations":[{"action":"","steps":[],"pct_kwh_reduction_min":0,'
            '"pct_kwh_reduction_max":0,"est_cost":0,"notes":"","disruption":"medium"}]}'
        )

    sys_prompt = (
        sys_tmpl
        .replace("{BUDGET}", BUDGET)
        .replace("{PAYBACK}", PAYBACK)
        .replace("{CO2_GOAL}", CO2_GOAL)
        .replace("{MAX_DISRUPTION}", MAX_DISRUPTION)
    )
    return sys_prompt


def _shape_recommendations(obj: Dict[str, Any]) -> Recommendations:
    recs_list = obj.get("recommendations") if isinstance(obj, dict) else None
    if not isinstance(recs_list, list):
        recs_list = []

    cleaned: List[Recommendation] = []
    for item in recs_list:
        if not isinstance(item, dict):
            continue
        try:
            cleaned.append(Recommendation(**item))
        except Exception:
            action = item.get("action")
            pct_min = item.get("pct_kwh_reduction_min")
            pct_max = item.get("pct_kwh_reduction_max")
            est_cost = item.get("est_cost")
            if action is not None and pct_min is not None and pct_max is not None and est_cost is not None:
                cleaned.append(
                    Recommendation(
                        action=str(action),
                        steps=[s for s in item.get("steps", []) if isinstance(s, str)],
                        pct_kwh_reduction_min=float(pct_min),
                        pct_kwh_reduction_max=float(pct_max),
                        est_cost=float(est_cost),
                        notes=item.get("notes") or "",
                        disruption=str(item.get("disruption", "medium")).lower(),
                        kwh_saved_per_month=float(item.get("kwh_saved_per_month")) if item.get("kwh_saved_per_month") is not None else None,
                        payback_months=float(item.get("payback_months")) if item.get("payback_months") is not None else None,
                    )
                )
    return Recommendations(recommendations=cleaned)



def compose_recommendations(normalized: NormalizedInput, findings: AuditResult) -> Recommendations:
    sys_prompt = _build_system_prompt(
        policy=normalized.policy.model_dump() if normalized.policy else None
    )
    user_payload: Dict[str, Any] = {
        "context": {
            "tariff_LKR_per_kWh": normalized.tariff_LKR_per_kWh,
            "monthly_kWh": normalized.monthly_kWh,
            "floor_area_m2": normalized.floor_area_m2,
            "ac_units": [ac.model_dump() for ac in normalized.ac_units],
            "lighting": normalized.lighting.model_dump() if normalized.lighting else None,
            "policy": normalized.policy.model_dump() if normalized.policy else None,
        },
        "audit_summary": {
            "findings": [f.model_dump() for f in (findings.findings or [])],
        },
        "instructions": "Return exactly one JSON object as specified in the system prompt. No prose, no markdown.",
    }
    raw: Dict[str, Any] = {}
    try:
        raw = call_json(system_text=sys_prompt, user_content=user_payload) or {}
    except Exception:
        raw = {}

    recs = _shape_recommendations(raw)
    recs_filtered, report = apply_policy(recs, normalized)
    recs_filtered.policy_report = report

    return recs_filtered

