# agents/planner_types.py
from __future__ import annotations
from typing import Any, Dict, Protocol, Tuple

class PlanStep(Protocol):
    def __call__(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

class ActStep(Protocol):
    def __call__(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        ...

class CheckStep(Protocol):
    def __call__(self, result: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Returns (ok, reason, patch)
        - ok: did we meet criteria?
        - reason: human-friendly summary
        - patch: minimal changes to apply to raw payload before a retry (e.g., add policy caps)
        """
        ...
