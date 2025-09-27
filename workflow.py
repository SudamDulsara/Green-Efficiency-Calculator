from agents.intake_agent import normalize
from agents.efficiency_auditor import audit
from agents.recommendation_composer import compose_recs
from agents.impact_estimator import estimate_impact

def run_workflow(input_payload: dict) -> dict:
    data = normalize(input_payload)
    findings = audit(data)
    recs = compose_recs(data, findings)
    plan = estimate_impact(data, recs)
    return {"input": data, "findings": findings, "plan": plan}
