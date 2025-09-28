from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from typing import Any, Dict
from dotenv import load_dotenv

from agents.intake_agent import normalize
from agents.efficiency_auditor import audit
from agents.recommendation_composer import compose_recs
from agents.impact_estimator import estimate_impact
from utils.models import (NormalizedInput, AuditResult, Recommendations, ImpactPlan, RawPayload, ComposeInput, EstimateInput)
from workflow import run_workflow


load_dotenv()

app = FastAPI(
    title="Green Efficiency Calculator APIs",
    version="1.0.0",
    description="Public endpoints exposing the agent workflow and their contracts."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

# @app.get("/")
# def root():
#     return {
#         "service": "Green Efficiency Calculator API",
#         "docs": "/docs",
#         "health": "/healthz",
#         "endpoints": ["/v1/normalize","/v1/audit","/v1/compose","/v1/estimate","/v1/run"]
#     }

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/v1/normalize", response_model=NormalizedInput)
def normalize_endpoint(req: RawPayload):
    out = normalize(req.payload)
    return NormalizedInput.model_validate(out)

@app.post("/v1/audit", response_model=AuditResult)
def audit_endpoint(req: NormalizedInput):
    out = audit(req.model_dump())
    return AuditResult.model_validate(out)

@app.post("/v1/compose", response_model=Recommendations)
def compose_endpoint(req: ComposeInput):
    out = compose_recs(req.normalized.model_dump(), req.findings.model_dump())
    return Recommendations.model_validate(out)

@app.post("/v1/estimate", response_model=ImpactPlan)
def estimate_endpoint(req: EstimateInput):
    out = estimate_impact(req.normalized.model_dump(), req.recommendations.model_dump())
    return ImpactPlan.model_validate(out)

@app.post("/v1/run", response_model=Dict[str, Any])
def run_endpoint(req: RawPayload):
    return run_workflow(req.payload)
