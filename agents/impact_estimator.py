from __future__ import annotations
from typing import Dict, Any, List, Tuple
from math import isfinite

from utils.yaml_loader import load_defaults
from utils.models import NormalizedInput, Recommendations, Recommendation, ImpactAction, ImpactTotals, ImpactPlan

def _num(x, default=0.0) -> float:
    try:
        v = float(x)
        return v if isfinite(v) else default
    except Exception:
        return default


def _est_kwh_saved_per_month(rec: Recommendation, baseline_kwh: float) -> float:
    if rec.kwh_saved_per_month is not None:
        return max(_num(rec.kwh_saved_per_month, 0.0), 0.0)

    pct_min = max(_num(rec.pct_kwh_reduction_min, 0.0), 0.0)
    pct_min = min(pct_min, 100.0)
    return baseline_kwh * (pct_min / 100.0)


def _monthly_savings_LKR(kwh_saved: float, tariff: float) -> float:
    return max(kwh_saved * max(tariff, 0.0), 0.0)


def _payback_months(cost_LKR: float, monthly_savings_LKR: float, fallback: float | None) -> float | None:
    if fallback is not None and _num(fallback, -1.0) >= 0:
        return float(fallback)
    if monthly_savings_LKR > 0:
        return cost_LKR / monthly_savings_LKR
    return None


def _mk_action(rec: Recommendation, baseline_kwh: float, tariff: float, ef_kg_per_kwh: float) -> ImpactAction:
    kwh = _est_kwh_saved_per_month(rec, baseline_kwh)
    lkr = _monthly_savings_LKR(kwh, tariff)
    co2 = max(kwh * max(ef_kg_per_kwh, 0.0), 0.0)
    cost = max(_num(rec.est_cost, 0.0), 0.0)

    return ImpactAction(
        action=rec.action,
        kWh_saved_per_month=kwh,
        LKR_saved_per_month=lkr,
        est_cost=cost,
        notes=rec.notes or "",
        co2_kg_saved_per_month=co2,
        disruption=(rec.disruption or "medium"),
        payback_months=_payback_months(cost, lkr, rec.payback_months),
    )

def estimate_impact(normalized: NormalizedInput, recs: Recommendations) -> ImpactPlan:
    defs = load_defaults()
    ef = float(defs.get("emission_factor_kg_per_kwh", 0.6))

    baseline_kwh = max(_num(normalized.monthly_kWh, 0.0), 0.0)
    tariff = max(_num(normalized.tariff_LKR_per_kWh, 0.0), 0.0)

    actions: List[ImpactAction] = []
    for r in (recs.recommendations or []):
        try:
            actions.append(_mk_action(r, baseline_kwh, tariff, ef))
        except Exception:
            continue

    total_kwh = sum(a.kWh_saved_per_month for a in actions)
    total_lkr = sum(a.LKR_saved_per_month for a in actions)
    total_co2 = sum(a.co2_kg_saved_per_month for a in actions)

    totals = ImpactTotals(
        kWh_saved_per_month=total_kwh,
        LKR_saved_per_month=total_lkr,
        co2_kg_saved_per_month=total_co2,
    )

    cheap_cap = 10_000.0
    fast_pb = 6.0
    quick_wins = [
        a for a in actions
        if (a.est_cost <= cheap_cap) or (a.payback_months is not None and a.payback_months <= fast_pb)
    ]
    quick_wins = sorted(
        quick_wins,
        key=lambda a: (
            a.est_cost,
            (a.payback_months if a.payback_months is not None else 1e9),
            -a.kWh_saved_per_month,
        ),
    )

    achieved_pct_kwh = (totals.kWh_saved_per_month / baseline_kwh * 100.0) if baseline_kwh > 0 else 0.0
    achieved_pct_co2 = (totals.co2_kg_saved_per_month / (baseline_kwh * ef) * 100.0) if baseline_kwh > 0 else 0.0

    lines: List[str] = []
    lines.append("### Action Plan")
    lines.append(f"- Estimated monthly savings: **{round(totals.LKR_saved_per_month, 2):,} LKR**")
    lines.append(f"- Energy reduction: **{round(totals.kWh_saved_per_month, 2):,} kWh/mo** (~{round(achieved_pct_kwh, 1)}%)")
    lines.append(f"- CO₂ reduction: **{round(totals.co2_kg_saved_per_month, 2):,} kgCO₂/mo** (~{round(achieved_pct_co2, 1)}%)")

    if quick_wins:
        lines.append("\n**Quick wins (low cost / fast payback):**")
        for a in quick_wins:
            pb_txt = f", payback ~{round(a.payback_months, 1)} mo" if a.payback_months is not None else ""
            lines.append(
                f"- {a.action}: ~{round(a.kWh_saved_per_month,1)} kWh/mo, ~{round(a.LKR_saved_per_month,0):,} LKR/mo, capex ~{round(a.est_cost,0):,} LKR{pb_txt}"
            )

    warn_unmet = False
    if normalized.policy and normalized.policy.co2_reduction_goal_pct is not None:
        goal = float(normalized.policy.co2_reduction_goal_pct)
        if achieved_pct_co2 + 1e-9 < goal:
            warn_unmet = True
            lines.append(
                f"\n> ⚠️ **CO₂ goal not fully met**: achieved ~{round(achieved_pct_co2,1)}% vs goal {goal}%."
                " Consider higher-impact actions or relaxing budget/payback constraints."
            )

    plan_text = "\n".join(lines)

    plan = ImpactPlan(
        quick_wins=quick_wins,
        all_actions=actions,
        totals=totals,
        plan_text=plan_text,
        policy=normalized.policy,
    )
    return plan
