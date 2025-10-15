from __future__ import annotations
from typing import Any, Dict, Tuple

from utils.models import (
    NormalizedInput, AuditResult, Recommendations, ImpactPlan
)
from agents import (
    intake_agent,
    efficiency_auditor,
    recommendation_composer,
    policy_agent,
    impact_estimator,
)

def act_full_pipeline(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs your existing pipeline exactly once.
    """
    raw = plan["inputs"] or {}

    normalized_any = intake_agent.normalize(raw or {})
    normalized = normalized_any if isinstance(normalized_any, NormalizedInput) else NormalizedInput(**normalized_any)

    findings_any = efficiency_auditor.audit(normalized)
    findings = findings_any if isinstance(findings_any, AuditResult) else AuditResult(**findings_any)

    recs_any = recommendation_composer.compose_recommendations(normalized, findings)
    if isinstance(recs_any, dict):
        recs_dict = recs_any
    else:
        recs_dict = {"recommendations": [r.model_dump() for r in recs_any.recommendations]}

    filtered_dict, policy_report = policy_agent.enforce_policy(
        recommendations=recs_dict,
        policy=normalized.policy.model_dump() if normalized.policy else None,
        baseline_kwh=normalized.monthly_kWh or 0.0,
        tariff_LKR_per_kWh=normalized.tariff_LKR_per_kWh or 0.0,
    )
    recs = Recommendations(**filtered_dict, policy_report=policy_report)

    plan_any = impact_estimator.estimate_impact(normalized, recs)
    plan_out = plan_any if isinstance(plan_any, ImpactPlan) else ImpactPlan(**plan_any)

    return {
        "normalized": normalized,
        "findings": findings,
        "recommendations": recs,
        "policy_report": policy_report,
        "impact_plan": plan_out,
    }
