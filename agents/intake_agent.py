import json, os, yaml
from pathlib import Path
from utils.guardrails import clamp_hours, clamp_watts, clamp_count, clamp_kwh
from utils.llm import call_json

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "intake_system.txt"
DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "defaults.yaml"

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def normalize(input_payload: dict) -> dict:
    defaults = yaml.safe_load(DEFAULTS_PATH.read_text(encoding="utf-8"))
    tariff_default = float(defaults.get("tariff_LKR_per_kWh_default", 62))

    ac_units = input_payload.get("ac_units") or []
    fixed_ac = []
    for ac in ac_units:
        fixed_ac.append({
            "watt": clamp_watts(ac.get("watt", 0)),
            "hours_per_day": clamp_hours(ac.get("hours_per_day", 0)),
            "star_rating": int(max(1, min(5, float(ac.get("star_rating", 3))))),
        })

    lighting = input_payload.get("lighting") or {}
    lighting_fixed = {
        "bulbs": clamp_count(lighting.get("bulbs", 0)),
        "watt_per_bulb": clamp_watts(lighting.get("watt_per_bulb", defaults["lighting"]["non_led_watt_per_bulb"])),
        "hours_per_day": clamp_hours(lighting.get("hours_per_day", 4)),
    }

    data_local = {
        "floor_area_m2": float(input_payload.get("floor_area_m2", 0)),
        "ac_units": fixed_ac,
        "lighting": lighting_fixed,
        "tariff_LKR_per_kWh": float(input_payload.get("tariff_LKR_per_kWh", tariff_default)),
        "monthly_kWh": clamp_kwh(input_payload.get("monthly_kWh", 0)),
    }

    system_prompt = _read(PROMPT_PATH)
    user_prompt = f"Normalize this input conservatively:\n{json.dumps(data_local, ensure_ascii=False)}"
    result = call_json(system_prompt, user_prompt)

    result["monthly_kWh"] = clamp_kwh(result.get("monthly_kWh", data_local["monthly_kWh"]))
    result["tariff_LKR_per_kWh"] = float(result.get("tariff_LKR_per_kWh", data_local["tariff_LKR_per_kWh"]))
    return result
