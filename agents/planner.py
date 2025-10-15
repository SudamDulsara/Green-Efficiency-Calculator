from __future__ import annotations
from typing import Any, Dict, List, Optional

from agents.planner_types import PlanStep, ActStep, CheckStep
from agents.steps.plan_default import default_plan_step
from agents.steps.act_full_pipeline import act_full_pipeline
from agents.steps.check_default import check_against_criteria

def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

class TinyPlanner:
    def __init__(
        self,
        max_iters: int = 2,
        plan_step: PlanStep = default_plan_step,
        act_step: ActStep = act_full_pipeline,
        check_step: CheckStep = check_against_criteria,
    ):
        self.max_iters = max(1, min(max_iters, 3))
        self.plan_step = plan_step
        self.act_step = act_step
        self.check_step = check_step

    def plan(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.plan_step(raw_payload)

    def act(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return self.act_step(plan)

    def check(self, result: Dict[str, Any], criteria: Dict[str, Any]):
        return self.check_step(result, criteria)

    def run(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        attempts: List[Dict[str, Any]] = []
        last_result: Optional[Dict[str, Any]] = None
        payload = dict(raw_payload)

        for i in range(self.max_iters):
            plan = self.plan(payload)
            result = self.act(plan)
            ok, reason, patch = self.check(result, plan.get("criteria", {}))
            attempts.append(
                {
                    "attempt": i + 1,
                    "plan": plan,
                    "ok": ok,
                    "reason": reason,
                    "patch_applied_next": bool(patch) and not ok and (i + 1) < self.max_iters,
                }
            )
            last_result = result
            if ok:
                break
            if patch:
                payload = _deep_merge(payload, patch)

        return {
            "planner_trace": attempts,
            "final": last_result,
        }
