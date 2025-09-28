from __future__ import annotations
import os, json, pathlib, uuid, time
from typing import Dict, Any, List, Tuple

from utils.messages import Message, TraceEvent
from agents.intake_agent import normalize
from agents.efficiency_auditor import audit
from agents.recommendation_composer import compose_recs
from agents.impact_estimator import estimate_impact
from utils.models import (NormalizedInput, AuditResult, Recommendations, ImpactPlan)
from utils.checks import consistency_checks
from tools.tariff_retriever import get_tariff
from tools.bill_parser import parse_bill_text

LOG_DIR = pathlib.Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _log_event(trace_id: str, step: str, msg: Message) -> None:
    rec = TraceEvent(trace_id=trace_id, step=step, msg=msg)
    p = LOG_DIR / f"{trace_id}.jsonl"
    with open(p, "a", encoding="utf-8") as f:
        f.write(rec.model_dump_json() + "\n")

def _initial_plan(input_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Minimal planner: pick steps based on missing data.
    """
    steps: List[Dict[str, Any]] = []

    if input_payload.get("bill_text"):
        steps.append({"agent": "tool", "intent": "parse_bill"})

    steps.append({"agent": "intake", "intent": "normalize"})

    steps.append({"agent": "tool", "intent": "lookup_tariff"})

    steps.append({"agent": "auditor", "intent": "audit"})
    steps.append({"agent": "recommender", "intent": "recommend"})
    steps.append({"agent": "estimator", "intent": "estimate"})
    return steps

def _apply_step(state: Dict[str, Any], step: Dict[str, Any], trace_id: str) -> Tuple[Dict[str, Any], Message]:
    agent = step["agent"]
    intent = step["intent"]

    if agent == "tool" and intent == "parse_bill":
        msg = Message(role="tool", intent="parse_bill", payload={"input": list(state.keys())}, trace_id=trace_id)
        _log_event(trace_id, "call", msg)
        parsed = parse_bill_text(state.get("bill_text", "") or "")
        state.update(parsed or {})
        msg_out = Message(role="tool", intent="parse_bill", payload=parsed or {}, trace_id=trace_id)
        _log_event(trace_id, "return", msg_out)
        return state, msg_out

    if agent == "intake" and intent == "normalize":
        msg = Message(role="coordinator", intent="normalize", payload={"input": list(state.keys())}, trace_id=trace_id)
        _log_event(trace_id, "call", msg)
        data = normalize(state)  # dict
        state["normalized"] = NormalizedInput.model_validate(data).model_dump()
        msg_out = Message(role="intake", intent="normalize", payload=state["normalized"], trace_id=trace_id)
        _log_event(trace_id, "return", msg_out)
        return state, msg_out

    if agent == "tool" and intent == "lookup_tariff":
        if not state.get("normalized", {}).get("tariff_LKR_per_kWh"):
            region = state.get("region") or state.get("normalized", {}).get("region")
            t = get_tariff(region)
            state["normalized"]["tariff_LKR_per_kWh"] = float(t)
        msg_out = Message(role="tool", intent="lookup_tariff", payload={"tariff_LKR_per_kWh": state["normalized"].get("tariff_LKR_per_kWh")}, trace_id=trace_id)
        _log_event(trace_id, "return", msg_out)
        return state, msg_out

    if agent == "auditor" and intent == "audit":
        msg = Message(role="coordinator", intent="audit", payload={"normalized_keys": list(state["normalized"].keys())}, trace_id=trace_id)
        _log_event(trace_id, "call", msg)
        findings = audit(state["normalized"])
        state["findings"] = AuditResult.model_validate(findings).model_dump()
        msg_out = Message(role="auditor", intent="audit", payload=state["findings"], trace_id=trace_id)
        _log_event(trace_id, "return", msg_out)
        return state, msg_out

    if agent == "recommender" and intent == "recommend":
        msg = Message(role="coordinator", intent="recommend", payload={"normalized": list(state["normalized"].keys()), "findings_count": len(state.get("findings", {}).get("findings", []))}, trace_id=trace_id)
        _log_event(trace_id, "call", msg)
        recs = compose_recs(state["normalized"], state["findings"])
        state["recs"] = Recommendations.model_validate(recs).model_dump()
        msg_out = Message(role="recommender", intent="recommend", payload=state["recs"], trace_id=trace_id)
        _log_event(trace_id, "return", msg_out)
        return state, msg_out

    if agent == "estimator" and intent == "estimate":
        msg = Message(role="coordinator", intent="estimate", payload={"normalized": True, "recs": True}, trace_id=trace_id)
        _log_event(trace_id, "call", msg)
        plan = estimate_impact(state["normalized"], state["recs"])
        plan = ImpactPlan.model_validate(plan).model_dump()
        plan_fixed, flags = consistency_checks(state["normalized"], plan)
        state["plan"] = plan_fixed
        state["flags"] = flags
        msg_out = Message(role="estimator", intent="estimate", payload={"plan": plan_fixed, "flags": flags}, trace_id=trace_id)
        _log_event(trace_id, "return", msg_out)
        return state, msg_out

    msg_out = Message(role="coordinator", intent=intent, status="error", notes="Unknown step", trace_id=trace_id)
    _log_event(trace_id, "error", msg_out)
    return state, msg_out

def run_agentic(input_payload: Dict[str, Any], *, max_iters: int = 2) -> Dict[str, Any]:
    """
    Coordinator loop: plan -> act -> observe (with small retry budget).
    """
    trace_id = str(uuid.uuid4())
    state: Dict[str, Any] = dict(input_payload or {})
    plan = _initial_plan(state)

    _log_event(trace_id, "plan", Message(role="coordinator", intent="plan", payload={"steps": plan}, trace_id=trace_id))

    errors = 0
    for _ in range(max_iters):
        for step in plan:
            try:
                state, msg = _apply_step(state, step, trace_id)
                if msg.status == "error":
                    errors += 1
                    if errors > 2:
                        break
            except Exception as e:
                _log_event(trace_id, "exception", Message(role="coordinator", intent=step["intent"], status="error", notes=str(e), trace_id=trace_id))
                errors += 1
                if errors > 2:
                    break
        if errors <= 2:
            break

    return {
        "trace_id": trace_id,
        "input": input_payload,
        "normalized": state.get("normalized"),
        "findings": state.get("findings"),
        "recommendations": state.get("recs"),
        "plan": state.get("plan"),
        "flags": state.get("flags", []),
    }
