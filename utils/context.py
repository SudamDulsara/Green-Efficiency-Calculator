from __future__ import annotations
from typing import Optional
from .autofix import AutoFixContext

def make_autofix_ctx(
    tariff_per_kwh: Optional[float] = None,
    grid_kg_per_kwh: Optional[float] = None,
) -> AutoFixContext:
    if tariff_per_kwh is None:
        tariff_per_kwh = 0.20
    if grid_kg_per_kwh is None:
        grid_kg_per_kwh = 0.70
    return AutoFixContext(
        tariff_per_kwh=float(tariff_per_kwh),
        grid_kg_per_kwh=float(grid_kg_per_kwh),
    )
