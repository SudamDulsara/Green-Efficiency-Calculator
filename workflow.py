from agents.intake_agent import normalize
from agents.efficiency_auditor import audit
from agents.recommendation_composer import compose_recs
from agents.impact_estimator import estimate_impact

from utils.models import (NormalizedInput, AuditResult, Recommendations, ImpactPlan)


def run_workflow(input_payload: dict) -> dict:
    """
    Protocol (v1):
      - normalize(input_payload: dict) -> NormalizedInput
      - audit(NormalizedInput) -> AuditResult
      - compose_recs(NormalizedInput, AuditResult) -> Recommendations
      - estimate_impact(NormalizedInput, Recommendations) -> ImpactPlan

    Returns a JSON-serializable dict with keys: input, findings, plan.
    """

    data_dict = normalize(input_payload)
    data = NormalizedInput.model_validate(data_dict)

    findings_dict = audit(data.model_dump())
    findings = AuditResult.model_validate(findings_dict)

    recs_dict = compose_recs(data.model_dump(), findings.model_dump())
    recs = Recommendations.model_validate(recs_dict)

    plan_dict = estimate_impact(data.model_dump(), recs.model_dump())
    plan = ImpactPlan.model_validate(plan_dict)

    return {
        "input": data.model_dump(),
        "findings": findings.model_dump(),
        "plan": plan.model_dump(),
    }
