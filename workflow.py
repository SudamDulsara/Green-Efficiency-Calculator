from __future__ import annotations
from typing import Any, Dict, Tuple, List

from agents import intake_agent
from agents import efficiency_auditor
from agents import recommendation_composer
from agents import impact_estimator
from agents import policy_agent
from agents.planner import TinyPlanner

from utils.models import NormalizedInput, AuditResult, Recommendations, ImpactPlan
from utils.validation import validate_actions_report
from utils.autofix import AutoFixContext


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


def _derive_ctx_from_sources(
    normalized_like: Any | None,
    raw_payload: Dict[str, Any] | None,
    input_dict_like: Dict[str, Any] | None = None,
) -> AutoFixContext:
    tariff_ctx = None
    grid_ctx = None

    if normalized_like is not None:
        if hasattr(normalized_like, "tariff_per_kwh"):
            tariff_ctx = getattr(normalized_like, "tariff_per_kwh")
        if hasattr(normalized_like, "grid_kg_per_kwh"):
            grid_ctx = getattr(normalized_like, "grid_kg_per_kwh")
        if tariff_ctx is None and hasattr(normalized_like, "tariff_LKR_per_kWh"):
            tariff_ctx = getattr(normalized_like, "tariff_LKR_per_kWh")

    if input_dict_like and isinstance(input_dict_like, dict):
        if tariff_ctx is None:
            tariff_ctx = input_dict_like.get("tariff_per_kwh") or input_dict_like.get("tariff_LKR_per_kWh")
        if grid_ctx is None:
            grid_ctx = input_dict_like.get("grid_kg_per_kwh")

    if raw_payload and isinstance(raw_payload, dict):
        if tariff_ctx is None:
            tariff_ctx = raw_payload.get("tariff_per_kwh") or raw_payload.get("tariff_LKR_per_kWh")
        if grid_ctx is None:
            grid_ctx = raw_payload.get("grid_kg_per_kwh")

    if tariff_ctx is None:
        tariff_ctx = 0.20
    if grid_ctx is None:
        grid_ctx = 0.70

    return AutoFixContext(
        tariff_per_kwh=float(tariff_ctx),
        grid_kg_per_kwh=float(grid_ctx),
    )


def _ensure_structured_actions_in_plan(
    plan_dict: Dict[str, Any] | None,
    normalized_like: Any | None,
    raw_payload: Dict[str, Any] | None,
    input_dict_like: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    plan_dict = dict(plan_dict or {})
    raw_actions: List[Dict[str, Any]] = plan_dict.get("actions", []) or []

    if not raw_actions:
        legacy = plan_dict.get("all_actions", []) or []
        for a in legacy:
            try:
                kwh_pm = float(a.get("kWh_saved_per_month", 0.0) or 0.0)
                lkr_pm = a.get("LKR_saved_per_month", None)
                raw_actions.append(
                    {
                        "action": a.get("action", "") or "Unnamed action",
                        "capex": float(a.get("est_cost", 0.0) or 0.0),
                        "annual_kWh_saved": kwh_pm * 12.0,
                        "opex_change": -(float(lkr_pm) * 12.0) if lkr_pm not in (None, "") else None,
                        "CO2e_saved": float(a.get("co2_kg_saved_per_month", 0.0) or 0.0) * 12.0,
                        "payback_months": float(a.get("payback_months", 0.0) or 0.0) or None,
                        "confidence": float(a.get("confidence", 0.7)),
                    }
                )
            except Exception:
                continue

    ctx = _derive_ctx_from_sources(normalized_like, raw_payload, input_dict_like)
    report = validate_actions_report(raw_actions, ctx=ctx, strict=False)

    plan_dict["actions"] = [obj.model_dump() for obj in report.objects]
    plan_dict["actions_structured"] = plan_dict["actions"]
    if report.issues:
        plan_dict["actions_invalid_issues"] = [
            f"row {i.row_index+1} · {i.field}: {i.message}" for i in report.issues
        ]
    plan_dict["actions_schema_version"] = "1.0.0"
    return plan_dict


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

    plan_dict = plan.model_dump()
    plan_dict = _ensure_structured_actions_in_plan(
        plan_dict=plan_dict,
        normalized_like=normalized,
        raw_payload=raw_payload,
        input_dict_like=None,
    )

    return {
        "input": normalized.model_dump(),
        "findings": findings.model_dump(),
        "recommendations": recs_filtered.model_dump(),
        "plan": plan_dict,
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

    shaped["plan"] = _ensure_structured_actions_in_plan(
        plan_dict=shaped.get("plan") or {},
        normalized_like=final.get("normalized", None),
        raw_payload=raw_payload,
        input_dict_like=shaped.get("input") or {},
    )

    return shaped
