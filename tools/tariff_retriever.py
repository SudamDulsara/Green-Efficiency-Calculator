from __future__ import annotations
from typing import Optional

_TARIFF_LKR = {
    "LK:RES_LOW": 52.0,
    "LK:RES_MED": 65.0,
    "LK:RES_HIGH": 82.0,
    "LK:SME": 60.0,
    "LK:COMMERCIAL": 75.0,

    "default": 60.0,
}

def get_tariff(region_or_code: Optional[str]) -> float:
    """
    Return an estimated tariff (LKR/kWh) for a region or tariff code.
    - First try exact code match.
    - Then try fuzzy keyword buckets.
    - Finally return a conservative default.
    """
    if not region_or_code:
        return _TARIFF_LKR["default"]

    key = region_or_code.strip().upper()
    if key in _TARIFF_LKR:
        return _TARIFF_LKR[key]

    if "COMM" in key:
        return _TARIFF_LKR["LK:COMMERCIAL"]
    if "SME" in key or "SHOP" in key or "SMALL" in key:
        return _TARIFF_LKR["LK:SME"]
    if "RES" in key or "HOME" in key or "HOUSE" in key:
        return _TARIFF_LKR["LK:RES_MED"]

    return _TARIFF_LKR["default"]
