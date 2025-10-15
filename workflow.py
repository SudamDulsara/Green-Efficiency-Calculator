from __future__ import annotations
from typing import Any, Dict, Tuple

from agents import intake_agent
from agents import efficiency_auditor
from agents import recommendation_composer
from agents import impact_estimator
from agents import policy_agent
from agents.planner import TinyPlanner

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


def _compose_and_filter(
    normalized: NormalizedInput, findings: AuditResult
) -> Tuple[Recommendations, Dict[str, Any]]:
    """
    Helper that matches your current composer + policy agent behavior.
    - Uses recommendation_composer.compose_recommendations(...)
    - Uses policy_agent.enforce_policy(...)
    Returns (filtered_recommendations_model, policy_report_dict)
    """
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

    recs_filtered = Recommendations(**filtered_dict, policy_report=policy_report)
    return recs_filtered, policy_report


def _legacy_run_workflow(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Original (no-planner) pipeline:
      raw -> normalize -> audit -> compose -> POLICY.enforce_policy -> estimate
    """
    normalized_dict = intake_agent.normalize(raw_payload or {})
    normalized = _coerce_normalized(normalized_dict)

    findings_any = efficiency_auditor.audit(normalized)
    findings = _coerce_audit(findings_any)

    recs_filtered, _policy_report = _compose_and_filter(normalized, findings)

    plan_any = impact_estimator.estimate_impact(normalized, recs_filtered)
    plan = _coerce_plan(plan_any)

    return {
        "input": normalized.model_dump(),
        "findings": findings.model_dump(),
        "recommendations": recs_filtered.model_dump(),
        "plan": plan.model_dump(),
    }


def _shape_from_planner_final(final: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    The planner returns a dict with objects; convert to your stable API shape:
      { "input", "findings", "recommendations", "plan" }
    Handles both object instances and dicts defensively.
    """
    if not final:
        return {}

    normalized = final.get("normalized")
    if hasattr(normalized, "model_dump"):
        input_obj = normalized.model_dump()
    elif isinstance(normalized, dict):
        input_obj = normalized
    else:
        input_obj = {}

    findings = final.get("findings")
    if hasattr(findings, "model_dump"):
        findings_obj = findings.model_dump()
    elif isinstance(findings, dict):
        findings_obj = findings
    else:
        findings_obj = {}

    recs = final.get("recommendations")
    if hasattr(recs, "model_dump"):
        recs_obj = recs.model_dump()
    elif isinstance(recs, dict):
        recs_obj = recs
    else:
        recs_obj = {}

    plan_key = "plan"
    plan_val = final.get("plan") or final.get("impact_plan")
    if hasattr(plan_val, "model_dump"):
        plan_obj = plan_val.model_dump()
    elif isinstance(plan_val, dict):
        plan_obj = plan_val
    else:
        plan_obj = {}

    return {
        "input": input_obj,
        "findings": findings_obj,
        "recommendations": recs_obj,
        "plan": plan_obj,
    }


def run_workflow(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner-enabled workflow with backward-compatible output.
    Toggle with: payload.planner.enabled  (default True)
    """
    use_planner = bool(raw_payload.get("planner", {}).get("enabled", True))

    if not use_planner or TinyPlanner is None:
        return _legacy_run_workflow(raw_payload)

    planner = TinyPlanner(max_iters=2)
    out = planner.run(raw_payload)
    final = out.get("final") or {}

    shaped = _shape_from_planner_final(final)
    shaped["planner_trace"] = out.get("planner_trace", [])

    return shaped
