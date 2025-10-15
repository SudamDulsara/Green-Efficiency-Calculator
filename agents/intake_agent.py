import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from utils.guardrails import clamp_hours, clamp_watts, clamp_count, clamp_kwh, clamp_disruption
from utils.models import PolicyGoals

DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "defaults.yaml"

def _to_float(x) -> float | None:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None

def _to_int(x) -> int | None:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None

def _load_defaults() -> Dict[str, Any]:
    fallbacks: Dict[str, Any] = {
        "tariff_LKR_per_kWh_default": 62.0,
        "lighting": {
            "non_led_watt_per_bulb": 12.0,
        },
    }
    try:
        if DEFAULTS_PATH.exists():
            with DEFAULTS_PATH.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                if isinstance(loaded, dict):
                    out = fallbacks.copy()
                    lig = out.get("lighting", {}).copy()
                    lig.update((loaded.get("lighting") or {}))
                    out["lighting"] = lig
                    for k, v in loaded.items():
                        if k != "lighting":
                            out[k] = v
                    return out
    except Exception:
        pass
    return fallbacks



def _normalize_policy(raw_policy: Dict[str, Any] | None) -> Optional[PolicyGoals]:
    """
    Convert raw 'policy' dict into a PolicyGoals object with safe values.
    All fields are optional; we leave them as None if missing.
    """
    if not raw_policy or not isinstance(raw_policy, dict):
        return None

    budget = _to_float(raw_policy.get("target_budget_LKR"))
    if budget is not None and budget < 0:
        budget = 0.0

    payback = _to_int(raw_policy.get("payback_threshold_months"))
    if payback is not None and payback < 0:
        payback = 0

    co2_goal = _to_float(raw_policy.get("co2_reduction_goal_pct"))
    if co2_goal is not None:
        if co2_goal < 0:
            co2_goal = 0.0
        if co2_goal > 100:
            co2_goal = 100.0

    max_disr = clamp_disruption(raw_policy.get("max_disruption"))

    return PolicyGoals(
        target_budget_LKR=budget,
        payback_threshold_months=payback,
        co2_reduction_goal_pct=co2_goal,
        max_disruption=max_disr,
    )

def normalize(input_payload: dict) -> dict:
    input_payload = input_payload or {}
    defaults = _load_defaults()

    tariff_default = float(defaults.get("tariff_LKR_per_kWh_default", 62.0))
    non_led_watt = float((defaults.get("lighting") or {}).get("non_led_watt_per_bulb", 12.0))

    ac_units_in = input_payload.get("ac_units") or []
    fixed_ac = []
    for ac in ac_units_in:
        ac = ac or {}
        fixed_ac.append(
            {
                "count": clamp_count(ac.get("count", 1)),
                "watt": clamp_watts(ac.get("watt", 0)),
                "hours_per_day": clamp_hours(ac.get("hours_per_day", 0)),
                "star_rating": max(1, min(5, int(float(ac.get("star_rating", 3))))),
            }
        )

    lighting_in = input_payload.get("lighting") or {}
    lighting_fixed = {
        "bulbs": clamp_count(lighting_in.get("bulbs", 0)),
        "watt_per_bulb": clamp_watts(lighting_in.get("watt_per_bulb", non_led_watt)),
        "hours_per_day": clamp_hours(lighting_in.get("hours_per_day", 4)),
    }

    try:
        floor_area = float(input_payload.get("floor_area_m2", 0.0))
        if floor_area < 0:
            floor_area = 0.0
    except Exception:
        floor_area = 0.0

    try:
        tariff = float(input_payload.get("tariff_LKR_per_kWh", tariff_default))
        if tariff < 0:
            tariff = tariff_default
    except Exception:
        tariff = tariff_default

    monthly_kwh = clamp_kwh(input_payload.get("monthly_kWh", 0.0))

    policy_obj = _normalize_policy(input_payload.get("policy"))

    data = {
        "floor_area_m2": floor_area,
        "ac_units": fixed_ac,
        "lighting": lighting_fixed,
        "tariff_LKR_per_kWh": tariff,
        "monthly_kWh": monthly_kwh,
        "policy": policy_obj.model_dump() if policy_obj else None,
    }
    return data