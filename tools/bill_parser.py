from __future__ import annotations
import re
from typing import Dict, Any, Optional

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

_KWH_PATTERNS = [
    r"(?i)\b(consumption|usage|kwh used|energy)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*kwh\b",
    r"(?i)\b([0-9]+(?:\.[0-9]+)?)\s*kwh\b",
]

_TARIFF_PATTERNS = [
    r"(?i)\b(tariff|rate|per\s*kwh)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(lkr|rs|rupees)?\s*/?\s*kwh\b",
    r"(?i)\b([0-9]+(?:\.[0-9]+)?)\s*(lkr|rs|rupees)\s*/?\s*kwh\b",
]

def _extract_first_match(text: str, patterns) -> Optional[float]:
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            for g in m.groups():
                if g and re.match(r"^[0-9]+(\.[0-9]+)?$", str(g)):
                    try:
                        return float(g)
                    except Exception:
                        pass
    return None

def parse_bill_text(text: str) -> Dict[str, Any]:
    """
    Extract simple monthly kWh and tariff (LKR/kWh) from bill text.
    Returns dict with any values it can find.
    """
    d: Dict[str, Any] = {}
    if not text:
        return d

    kwh = _extract_first_match(text, _KWH_PATTERNS)
    tariff = _extract_first_match(text, _TARIFF_PATTERNS)

    if kwh is not None:
        d["monthly_kWh"] = kwh
    if tariff is not None:
        d["tariff_LKR_per_kWh"] = tariff
    return d

def parse_pdf_bill(path: str) -> Dict[str, Any]:
    if PyPDF2 is None:
        return {}
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                try:
                    text += page.extract_text() or ""
                except Exception:
                    pass
        return parse_bill_text(text)
    except Exception:
        return {}