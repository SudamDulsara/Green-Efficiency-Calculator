import json
import math
from pathlib import Path
from utils.llm import call_json
from utils.guardrails import clamp

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "auditor_system.txt"

# Sri Lankan energy efficiency benchmarks
BENCHMARKS = {
    "energy_intensity": {
        "excellent": 8,   # kWh/m²/month
        "good": 12,
        "average": 18,
        "poor": 25
    },
    "ac_efficiency": {
        "min_star_rating": 3,
        "recommended_star_rating": 4,
        "max_hours_per_day": 12,
        "optimal_setpoint": 24  # °C
    },
    "lighting_efficiency": {
        "led_watt_per_bulb": 8,
        "cfl_watt_per_bulb": 15,
        "incandescent_watt_per_bulb": 60,
        "max_hours_per_day": 8
    },
    "usage_patterns": {
        "high_usage_threshold": 0.6,  # >60% of day
        "standby_power_limit": 10     # watts
    }
}

def _calculate_energy_intensity(normalized: dict) -> float:
    """Calculate energy intensity in kWh/m²/month"""
    monthly_kwh = float(normalized.get("monthly_kWh", 0))
    floor_area = float(normalized.get("floor_area_m2", 1))  # Avoid division by zero
    if floor_area <= 0:
        return 0
    return monthly_kwh / floor_area

def _analyze_usage_patterns(normalized: dict) -> list:
    """Analyze usage patterns for inefficiencies"""
    issues = []

    # Check AC usage patterns
    ac_units = normalized.get("ac_units", [])
    for i, ac in enumerate(ac_units):
        hours_per_day = ac.get("hours_per_day", 0)
        if hours_per_day > 18:  # >75% of day
            issues.append({
                "area": "operations",
                "issue": f"AC unit {i+1} operates {hours_per_day}h/day (excessive)",
                "severity": "high",
                "reason": "Near-continuous AC operation suggests poor building envelope or controls",
                "confidence": 0.8,
                "estimated_kwh_impact": ac.get("watt", 0) * 6 / 1000  # 6 hours reduction potential
            })

    # Check lighting usage patterns
    lighting = normalized.get("lighting", {})
    lighting_hours = lighting.get("hours_per_day", 0)
    if lighting_hours > 14:
        issues.append({
            "area": "operations",
            "issue": f"Lights operate {lighting_hours}h/day (likely excessive)",
            "severity": "med",
            "reason": "Extended lighting suggests poor daylight utilization or lack of controls",
            "confidence": 0.7,
            "estimated_kwh_impact": lighting.get("watt_per_bulb", 0) * lighting.get("bulbs", 0) * 4 / 1000
        })

    return issues

def _analyze_ac_efficiency(ac_units: list) -> list:
    """Analyze AC efficiency and return issues"""
    issues = []
    for i, ac in enumerate(ac_units):
        star_rating = ac.get("star_rating", 0)
        hours_per_day = ac.get("hours_per_day", 0)
        watt = ac.get("watt", 0)

        if star_rating < BENCHMARKS["ac_efficiency"]["min_star_rating"]:
            issues.append({
                "area": "AC",
                "issue": f"AC unit {i+1} has low efficiency rating ({star_rating} stars)",
                "severity": "high" if star_rating <= 2 else "med",
                "reason": f"Star rating below recommended minimum of {BENCHMARKS['ac_efficiency']['min_star_rating']}",
                "confidence": 0.9,
                "estimated_kwh_impact": watt * hours_per_day * 0.15 / 1000  # 15% improvement estimate
            })

        if hours_per_day > BENCHMARKS["ac_efficiency"]["max_hours_per_day"]:
            issues.append({
                "area": "AC",
                "issue": f"AC unit {i+1} operates {hours_per_day}h/day (excessive usage)",
                "severity": "med",
                "reason": f"Usage exceeds recommended {BENCHMARKS['ac_efficiency']['max_hours_per_day']}h/day",
                "confidence": 0.8,
                "estimated_kwh_impact": watt * (hours_per_day - BENCHMARKS["ac_efficiency"]["max_hours_per_day"]) / 1000
            })

    return issues

def _analyze_lighting_efficiency(lighting: dict) -> list:
    """Analyze lighting efficiency and return issues"""
    issues = []
    watt_per_bulb = lighting.get("watt_per_bulb", 0)
    bulbs = lighting.get("bulbs", 0)
    hours_per_day = lighting.get("hours_per_day", 0)

    if watt_per_bulb > BENCHMARKS["lighting_efficiency"]["led_watt_per_bulb"] * 1.5:
        severity = "high" if watt_per_bulb >= BENCHMARKS["lighting_efficiency"]["cfl_watt_per_bulb"] else "med"
        issues.append({
            "area": "lighting",
            "issue": f"High wattage bulbs ({watt_per_bulb}W per bulb)",
            "severity": severity,
            "reason": f"LED bulbs use only {BENCHMARKS['lighting_efficiency']['led_watt_per_bulb']}W for similar brightness",
            "confidence": 0.95,
            "estimated_kwh_impact": (watt_per_bulb - BENCHMARKS["lighting_efficiency"]["led_watt_per_bulb"]) * bulbs * hours_per_day / 1000
        })

    if hours_per_day > BENCHMARKS["lighting_efficiency"]["max_hours_per_day"]:
        issues.append({
            "area": "lighting",
            "issue": f"Lights used {hours_per_day}h/day (potentially excessive)",
            "severity": "low",
            "reason": "Consider motion sensors or daylight harvesting",
            "confidence": 0.6,
            "estimated_kwh_impact": watt_per_bulb * bulbs * (hours_per_day - BENCHMARKS["lighting_efficiency"]["max_hours_per_day"]) * 0.5 / 1000
        })

    return issues

def _analyze_overall_efficiency(normalized: dict) -> list:
    """Analyze overall building efficiency"""
    issues = []
    energy_intensity = _calculate_energy_intensity(normalized)

    if energy_intensity > BENCHMARKS["energy_intensity"]["poor"]:
        issues.append({
            "area": "envelope",
            "issue": f"Very high energy intensity ({energy_intensity:.1f} kWh/m²/month)",
            "severity": "high",
            "reason": f"Building uses {energy_intensity:.1f} kWh/m²/month, well above average of {BENCHMARKS['energy_intensity']['average']}",
            "confidence": 0.9,
            "estimated_kwh_impact": normalized.get("monthly_kWh", 0) * 0.2  # 20% potential reduction
        })
    elif energy_intensity > BENCHMARKS["energy_intensity"]["average"]:
        issues.append({
            "area": "envelope",
            "issue": f"Above-average energy intensity ({energy_intensity:.1f} kWh/m²/month)",
            "severity": "med",
            "reason": f"Building uses more energy than average ({BENCHMARKS['energy_intensity']['average']} kWh/m²/month)",
            "confidence": 0.8,
            "estimated_kwh_impact": normalized.get("monthly_kWh", 0) * 0.1  # 10% potential reduction
        })

    return issues

def audit(normalized: dict, max_findings: int = 5) -> dict:
    """
    Analyze a normalized input dictionary for inefficiencies using an LLM.
    Returns a dictionary with a 'findings' key containing up to max_findings inefficiencies.

    Args:
        normalized (dict): The normalized input data to audit.
        max_findings (int, optional): Maximum number of inefficiencies to list. Defaults to 5.

    Returns:
        dict: The LLM's response with identified inefficiencies under the 'findings' key.
    """
    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Failed to read system prompt: {e}"}

    # Perform quantitative analysis first
    quantitative_issues = []

    try:
        # Analyze AC efficiency
        ac_units = normalized.get("ac_units", [])
        quantitative_issues.extend(_analyze_ac_efficiency(ac_units))

        # Analyze lighting efficiency
        lighting = normalized.get("lighting", {})
        quantitative_issues.extend(_analyze_lighting_efficiency(lighting))

        # Analyze overall efficiency
        quantitative_issues.extend(_analyze_overall_efficiency(normalized))

    except Exception as e:
        return {"error": f"Failed during quantitative analysis: {e}"}

    # Sort by severity and impact, limit to max_findings
    severity_weights = {"high": 3, "med": 2, "low": 1}
    quantitative_issues.sort(key=lambda x: (
        severity_weights.get(x.get("severity", "low"), 1),
        x.get("estimated_kwh_impact", 0)
    ), reverse=True)

    quantitative_issues = quantitative_issues[:max_findings]

    # Enhanced LLM analysis with quantitative context
    try:
        energy_intensity = _calculate_energy_intensity(normalized)
        context = {
            "energy_intensity_kwh_per_m2": round(energy_intensity, 2),
            "quantitative_findings_count": len(quantitative_issues),
            "benchmarks": BENCHMARKS
        }

        jp = json.dumps(normalized, ensure_ascii=False)
        context_jp = json.dumps(context, ensure_ascii=False)

        user_prompt = (
            f"Analyze this building for energy inefficiencies with the provided context.\n"
            f"Building Data:\n{jp}\n\n"
            f"Analysis Context:\n{context_jp}\n\n"
            f"Focus on areas not covered by quantitative analysis. "
            f"Provide {max_findings - len(quantitative_issues)} additional findings if applicable.\n"
            'Return JSON with key "findings".'
        )

        llm_result = call_json(system_prompt, user_prompt)

        # Combine quantitative and LLM findings
        all_findings = quantitative_issues.copy()

        if "findings" in llm_result:
            for finding in llm_result["findings"]:
                # Add confidence and impact estimates to LLM findings
                finding["confidence"] = finding.get("confidence", 0.7)
                finding["estimated_kwh_impact"] = finding.get("estimated_kwh_impact", 0)
                all_findings.append(finding)

        # Final sort and limit
        all_findings.sort(key=lambda x: (
            severity_weights.get(x.get("severity", "low"), 1),
            x.get("confidence", 0.5),
            x.get("estimated_kwh_impact", 0)
        ), reverse=True)

        return {
            "findings": all_findings[:max_findings],
            "analysis_summary": {
                "energy_intensity_kwh_per_m2": round(energy_intensity, 2),
                "total_potential_monthly_savings_kwh": round(sum(f.get("estimated_kwh_impact", 0) for f in all_findings[:max_findings]), 2),
                "quantitative_findings": len(quantitative_issues),
                "llm_findings": len(llm_result.get("findings", []))
            }
        }

    except Exception as e:
        # Fallback to quantitative analysis only
        return {
            "findings": quantitative_issues,
            "analysis_summary": {
                "energy_intensity_kwh_per_m2": round(_calculate_energy_intensity(normalized), 2),
                "total_potential_monthly_savings_kwh": round(sum(f.get("estimated_kwh_impact", 0) for f in quantitative_issues), 2),
                "quantitative_findings": len(quantitative_issues),
                "llm_findings": 0
            },
            "warning": f"LLM analysis failed, using quantitative analysis only: {e}"
        }
