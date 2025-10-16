from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
from pydantic import ValidationError
from .models import StructuredAction
from .autofix import AutoFixContext, validate_and_autofix_action

@dataclass(frozen=True)
class ValidationIssue:
    row_index: int
    field: str
    message: str
    severity: str = "error"

@dataclass(frozen=True)
class ValidationOutput:
    objects: List[StructuredAction]
    notes_per_row: List[List[str]]
    issues: List[ValidationIssue]

def validate_actions_report(
    items: Iterable[Dict[str, Any]],
    ctx: AutoFixContext | None = None,
    strict: bool = False,
) -> ValidationOutput:
    ctx = ctx or AutoFixContext()
    objs: List[StructuredAction] = []
    notes: List[List[str]] = []
    issues: List[ValidationIssue] = []

    for i, item in enumerate(items):
        try:
            obj, ns = validate_and_autofix_action(item, ctx=ctx, strict=strict)
            objs.append(obj)
            notes.append(ns)
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(x) for x in (err.get("loc") or ())) or "unknown"
                msg = err.get("msg", "Validation error")
                issues.append(ValidationIssue(row_index=i, field=loc, message=msg, severity="error"))

    return ValidationOutput(objects=objs, notes_per_row=notes, issues=issues)
