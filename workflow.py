# workflow.py
from __future__ import annotations

from typing import Any, Dict

from agents import intake_agent
from agents import efficiency_auditor
from agents import recommendation_composer
from agents import impact_estimator
from agents import policy_agent

from utils.models import (
    NormalizedInput,
    AuditResult,
    Recommendations,
    ImpactPlan,
)


def _coerce_normalized(x: Dict[str, Any] | NormalizedInput) -> NormalizedInput:
    if isinstance(x, NormalizedInput):
        return x
    return NormalizedInput(**x)


def _coerce_audit(x: Dict[str, Any] | AuditResult) -> AuditResult:
    if isinstance(x, AuditResult):
        return x
    return AuditResult(**x)


def _coerce_recs(x: Dict[str, Any] | Recommendations) -> Recommendations:
    if isinstance(x, Recommendations):
        return x
    return Recommendations(**x)


def _coerce_plan(x: Dict[str, Any] | ImpactPlan) -> ImpactPlan:
    if isinstance(x, ImpactPlan):
        return x
    return ImpactPlan(**x)


def run_workflow(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    End-to-end pipeline with policy enforcement via a dedicated post-processor:
      raw -> normalize -> audit -> compose -> POLICY_AGENT.enforce_policy -> estimate
    Returns JSON-friendly dicts throughout.
    """
    # 1) Normalize
    normalized_dict = intake_agent.normalize(raw_payload or {})
    normalized = _coerce_normalized(normalized_dict)

    # 2) Audit
    findings_any = efficiency_auditor.audit(normalized)
    findings = _coerce_audit(findings_any)

    # 3) Compose (LLM or heuristic)
    recs_any = recommendation_composer.compose_recommendations(normalized, findings)

    # 4) Convert to plain dict for policy agent
    if isinstance(recs_any, dict):
        recs_dict = recs_any
    else:
        recs_dict = {"recommendations": [r.model_dump() for r in recs_any.recommendations]}

    # 5) Enforce policy deterministically (new agent)
    filtered_dict, policy_report = policy_agent.enforce_policy(
        recommendations=recs_dict,
        policy=normalized.policy.model_dump() if normalized.policy else None,
        baseline_kwh=normalized.monthly_kWh or 0.0,
        tariff_LKR_per_kWh=normalized.tariff_LKR_per_kWh or 0.0,
    )

    # 6) Coerce back to Recommendations (attach report)
    recs_filtered = Recommendations(**filtered_dict, policy_report=policy_report)

    # 7) Estimate impact using the filtered set
    plan_any = impact_estimator.estimate_impact(normalized, recs_filtered)
    plan = _coerce_plan(plan_any)

    # 8) Return JSON-friendly payload
    return {
        "input": normalized.model_dump(),
        "findings": findings.model_dump(),
        "recommendations": recs_filtered.model_dump(),
        "plan": plan.model_dump(),
    }
