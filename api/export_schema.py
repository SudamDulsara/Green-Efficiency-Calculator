"""
Exports JSON Schemas for the I/O contracts into docs/schemas/*.json
Run: python scripts/export_schema.py
"""
import json, os
from pathlib import Path
from utils.models import NormalizedInput, AuditResult, Recommendations, ImpactPlan

out_dir = Path("docs/schemas")
out_dir.mkdir(parents=True, exist_ok=True)

def dump(model, name):
    schema = model.model_json_schema()
    (out_dir / f"{name}.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print("Wrote", out_dir / f"{name}.json")

dump(NormalizedInput, "NormalizedInput")
dump(AuditResult, "AuditResult")
dump(Recommendations, "Recommendations")
dump(ImpactPlan, "ImpactPlan")
print("Done.")
