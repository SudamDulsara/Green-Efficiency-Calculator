from agents.intake_agent import normalize

payload = {
    "floor_area_m2": 120,
    "monthly_kWh": 320,
    "tariff_LKR_per_kWh": 62,
    "policy": {
        "target_budget_LKR": "150000",
        "payback_threshold_months": "12",
        "co2_reduction_goal_pct": 20,
        "max_disruption": "Low"
    }
}

ni = normalize(payload)
assert ni.policy is not None
assert ni.policy.target_budget_LKR == 150000.0
assert ni.policy.payback_threshold_months == 12
assert ni.policy.co2_reduction_goal_pct == 20.0
assert ni.policy.max_disruption == "low"
print("OK ✓")
