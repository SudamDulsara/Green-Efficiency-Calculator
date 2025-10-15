from __future__ import annotations
import os
import json
from functools import lru_cache
from typing import Any, Dict
import yaml

@lru_cache(maxsize=1)
def load_defaults() -> Dict[str, Any]:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, os.pardir))
    candidates = [
        os.path.join(root, "data", "defaults.yaml"),
        os.path.join(root, "data", "defaults.yml"),
    ]

    defaults: Dict[str, Any] = {}

    fallbacks: Dict[str, Any] = {
        "emission_factor_kg_per_kwh": 0.6,
        "disruption_order": ["none", "low", "medium", "high"],
    }

    for path in candidates:
        if os.path.exists(path) and yaml is not None:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                if isinstance(loaded, dict):
                    defaults.update(loaded)
                break
            except Exception:
                pass

    for k, v in fallbacks.items():
        defaults.setdefault(k, v)

    return defaults


if __name__ == "__main__":
    print(json.dumps(load_defaults(), indent=2))
