from __future__ import annotations
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from utils.models import (RawPayload, ComposeInput, EstimateInput, NormalizedInput, AuditResult, Recommendations, ImpactPlan,)
from agents import intake_agent, efficiency_auditor, recommendation_composer, impact_estimator
from workflow import run_workflow

app = FastAPI(
    title="Green Efficiency Calculator API",
    version="1.1.0",
    description=(
        "Energy efficiency pipeline (normalize → audit → compose → estimate). "
        "Now supports policy/goal inputs: target_budget_LKR, payback_threshold_months, "
        "co2_reduction_goal_pct, max_disruption."
    ),
)


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post(
    "/v1/normalize",
    response_model=NormalizedInput,
    summary="Normalize raw payload into canonical NormalizedInput (includes optional `policy`).",
)
def v1_normalize(req: RawPayload) -> NormalizedInput:
    normalized_dict = intake_agent.normalize(req.payload or {})
    return NormalizedInput(**normalized_dict)


@app.post(
    "/v1/audit",
    response_model=AuditResult,
    summary="Run quantitative/qualitative audit on a NormalizedInput.",
)
def v1_audit(body: NormalizedInput) -> AuditResult:
    res = efficiency_auditor.audit(body)
    return res if isinstance(res, AuditResult) else AuditResult(**res)


@app.post(
    "/v1/compose",
    response_model=Recommendations,
    summary="Compose recommendations under policy constraints (prompt + deterministic filtering).",
)
def v1_compose(body: ComposeInput) -> Recommendations:
    recs = recommendation_composer.compose_recommendations(body.normalized, body.findings)
    return recs if isinstance(recs, Recommendations) else Recommendations(**recs)


@app.post(
    "/v1/estimate",
    response_model=ImpactPlan,
    summary="Estimate monthly kWh/LKR/CO₂ impact (adds quick wins and CO₂ goal check).",
)
def v1_estimate(body: EstimateInput) -> ImpactPlan:
    plan = impact_estimator.estimate_impact(body.normalized, body.recommendations)
    return plan if isinstance(plan, ImpactPlan) else ImpactPlan(**plan)


@app.post(
    "/v1/run",
    response_model=Dict[str, Any],
    summary="End-to-end: raw payload → normalize → audit → compose → estimate.",
)
def v1_run(req: RawPayload) -> Dict[str, Any]:
    return run_workflow(req.payload or {})
