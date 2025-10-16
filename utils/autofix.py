from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from pydantic import ValidationError
from .models import StructuredAction


@dataclass(frozen=True)
class AutoFixContext:
    """
    Inputs used for inferring missing fields:
      - tariff_per_kwh: currency per kWh (float)
      - grid_kg_per_kwh: kg CO2e per kWh (float)
    """
    tariff_per_kwh: float | None = None
    grid_kg_per_kwh: float | None = None


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        sx = x.strip().replace(",", "")
        lower = sx.lower()
        mult = 1.0
        if lower.endswith("k"):
            mult, sx = 1_000.0, sx[:-1]
        elif lower.endswith("m"):
            mult, sx = 1_000_000.0, sx[:-1]
        try:
            return float(sx) * mult
        except ValueError:
            return None
    return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _compute_opex_change(annual_kwh_saved: float | None, tariff: float | None) -> float | None:
    """
    opex_change: annual operating expense delta; negative means savings.
    If we know annual kWh saved and tariff, infer opex_change = -annual_kwh_saved * tariff
    """
    if annual_kwh_saved is None or tariff is None:
        return None
    return -(annual_kwh_saved * tariff)


def _compute_co2e(annual_kwh_saved: float | None, grid_kg_per_kwh: float | None) -> float | None:
    if annual_kwh_saved is None or grid_kg_per_kwh is None:
        return None
    return annual_kwh_saved * grid_kg_per_kwh


def _compute_payback_months(capex: float | None, opex_change: float | None) -> float | None:
    """
    If opex_change < 0 (i.e., savings), payback_months = capex / (-(opex_change)/12)
    Otherwise undefined (no payback) -> return a very large sentinel value to keep schema valid.
    """
    if capex is None or opex_change is None:
        return None
    if opex_change < 0:
        monthly_savings = -opex_change / 12.0
        if monthly_savings > 0:
            return capex / monthly_savings
    return 1e9


def validate_and_autofix_action(
    payload: Mapping[str, Any],
    ctx: AutoFixContext | None = None,
    strict: bool = False,
) -> Tuple[StructuredAction, List[str]]:
    """
    Returns: (StructuredAction, fix_notes)
    - strict=False: attempt to coerce/fill; always return a valid StructuredAction or raise if impossible.
    - strict=True: only validate; do not modify/derive any fields (except type coercion of trivially safe casts).
    """
    ctx = ctx or AutoFixContext()
    fix_notes: List[str] = []
    data: Dict[str, Any] = dict(payload)

    for field in ("capex", "opex_change", "annual_kWh_saved", "CO2e_saved", "payback_months", "confidence"):
        if field in data:
            coerced = _to_float(data[field])
            if coerced is None and data[field] is not None:
                fix_notes.append(f"Could not coerce {field!r} from {data[field]!r}; leaving as-is for validator.")
            else:
                if coerced is not None and coerced != data[field]:
                    fix_notes.append(f"Coerced {field} -> {coerced}.")
                data[field] = coerced

    if data.get("confidence") is not None:
        before = data["confidence"]
        data["confidence"] = _clamp(float(before), 0.0, 1.0)
        if data["confidence"] != before:
            fix_notes.append(f"Clamped confidence from {before} to {data['confidence']} within [0,1].")

    if not strict:
        for nf in ("capex", "annual_kWh_saved", "CO2e_saved"):
            if data.get(nf) is not None and float(data[nf]) < 0:
                fix_notes.append(f"{nf} was negative ({data[nf]}). Set to 0.0 to respect schema.")
                data[nf] = 0.0

    if not strict:
        if data.get("opex_change") is None:
            oc = _compute_opex_change(_to_float(data.get("annual_kWh_saved")), ctx.tariff_per_kwh)
            if oc is not None:
                data["opex_change"] = oc
                fix_notes.append("Derived opex_change from annual_kWh_saved × tariff (negative = savings).")

        if data.get("CO2e_saved") is None:
            co2 = _compute_co2e(_to_float(data.get("annual_kWh_saved")), ctx.grid_kg_per_kwh)
            if co2 is not None:
                data["CO2e_saved"] = co2
                fix_notes.append("Derived CO2e_saved from annual_kWh_saved × grid_kg_per_kwh.")

        if data.get("payback_months") is None:
            pb = _compute_payback_months(_to_float(data.get("capex")), _to_float(data.get("opex_change")))
            if pb is not None:
                data["payback_months"] = pb
                if pb >= 1e9:
                    fix_notes.append("No savings (opex_change ≥ 0); set payback_months to a very large value.")
                else:
                    fix_notes.append("Derived payback_months from capex and opex_change (monthly savings).")

    try:
        obj = StructuredAction(**data)
        return obj, fix_notes
    except ValidationError as e:
        raise e


def validate_and_autofix_actions(
    items: Iterable[Mapping[str, Any]],
    ctx: AutoFixContext | None = None,
    strict: bool = False,
) -> Tuple[List[StructuredAction], List[List[str]]]:
    ctx = ctx or AutoFixContext()
    objs: List[StructuredAction] = []
    notes: List[List[str]] = []
    for item in items:
        obj, ns = validate_and_autofix_action(item, ctx=ctx, strict=strict)
        objs.append(obj)
        notes.append(ns)
    return objs, notes
