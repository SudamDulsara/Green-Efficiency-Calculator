from __future__ import annotations
from typing import Any, Dict
from utils.models import PlannerCriteria

def default_plan_step(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Default planner: run full pipeline once.
    Criteria pulled from payload.planner.criteria if present.
    """
    criteria_in = (raw_payload.get("planner", {}) or {}).get("criteria", {})
    crit = PlannerCriteria(**criteria_in)
    return {
        "name": "full_pipeline",
        "inputs": raw_payload,
        "criteria": crit.model_dump(),
    }
