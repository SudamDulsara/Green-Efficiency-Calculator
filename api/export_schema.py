from __future__ import annotations
import json
from pathlib import Path

from utils.models import (NormalizedInput, AuditResult, Recommendations, ImpactPlan, RawPayload, ComposeInput, EstimateInput,)

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "schemas"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _dump(model, name: str):
    schema = model.model_json_schema()
    (OUT_DIR / f"{name}.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

def main():
    _dump(RawPayload, "RawPayload")
    _dump(NormalizedInput, "NormalizedInput")
    _dump(AuditResult, "AuditResult")
    _dump(ComposeInput, "ComposeInput")
    _dump(Recommendations, "Recommendations")
    _dump(EstimateInput, "EstimateInput")
    _dump(ImpactPlan, "ImpactPlan")
    print(f"Wrote schemas to {OUT_DIR}")

if __name__ == "__main__":
    main()
