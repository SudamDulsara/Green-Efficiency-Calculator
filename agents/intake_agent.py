import yaml
from pathlib import Path
from utils.guardrails import clamp_hours, clamp_watts, clamp_count, clamp_kwh

DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "defaults.yaml"

def normalize(input_payload: dict) -> dict:
    """
    Deterministic intake: clamp and fill sane defaults without any LLM call.
    Output schema:
    {
      "floor_area_m2": number,
      "ac_units": [{"watt": number, "hours_per_day": number, "star_rating": number, "count": number}],
      "lighting": {"bulbs": number, "watt_per_bulb": number, "hours_per_day": number},
      "tariff_LKR_per_kWh": number,
      "monthly_kWh": number
    }
    """
    defaults = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8"))
    tariff_default = float(defaults.get("tariff_LKR_per_kWh_default", 62.0))
    non_led_watt = float(defaults.get("lighting", {}).get("non_led_watt_per_bulb", 12.0))

    ac_units_in = input_payload.get("ac_units") or []
    fixed_ac = []
    for ac in ac_units_in:
        fixed_ac.append({
            "count": clamp_count(ac.get("count", 1)),
            "watt": clamp_watts(ac.get("watt", 0)),
            "hours_per_day": clamp_hours(ac.get("hours_per_day", 0)),
            "star_rating": max(1, min(5, int(float(ac.get("star_rating", 3))))),
        })

    lighting_in = input_payload.get("lighting") or {}
    lighting_fixed = {
        "bulbs": clamp_count(lighting_in.get("bulbs", 0)),
        "watt_per_bulb": clamp_watts(lighting_in.get("watt_per_bulb", non_led_watt)),
        "hours_per_day": clamp_hours(lighting_in.get("hours_per_day", 4)),
    }

    data = {
        "floor_area_m2": float(input_payload.get("floor_area_m2", 0.0)),
        "ac_units": fixed_ac,
        "lighting": lighting_fixed,
        "tariff_LKR_per_kWh": float(input_payload.get("tariff_LKR_per_kWh", tariff_default)),
        "monthly_kWh": clamp_kwh(input_payload.get("monthly_kWh", 0.0)),
    }
    return data
