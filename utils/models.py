from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ACUnit(BaseModel):
    watt: float = 0.0
    hours_per_day: float = 0.0
    star_rating: float = 0.0
    count: int = 0


class Lighting(BaseModel):
    bulbs: int = 0
    watt_per_bulb: float = 0.0
    hours_per_day: float = 0.0


class NormalizedInput(BaseModel):
    """Canonical input that flows between agents."""
    model_config = ConfigDict(extra="ignore")
    floor_area_m2: float = 0.0
    ac_units: List[ACUnit] = Field(default_factory=list)
    lighting: Lighting = Field(default_factory=Lighting)
    tariff_LKR_per_kWh: float = 0.0
    monthly_kWh: float = 0.0

class Finding(BaseModel):
    area: Literal["lighting", "AC", "standby", "envelope", "other"]
    issue: str
    severity: Literal["low", "med", "high"]
    reason: str

    @field_validator("area", mode="before")
    @classmethod
    def _normalize_area(cls, v):
        if v is None:
            return "other"
        s = str(v).strip().lower()
        area_map = {
            "ac": "AC",
            "a/c": "AC",
            "aircon": "AC",
            "air-conditioning": "AC",
            "air_conditioning": "AC",
            "hvac": "AC",
            "lighting": "lighting",
            "lights": "lighting",
            "standby": "standby",
            "idle": "standby",
            "phantom": "standby",
            "envelope": "envelope",
            "insulation": "envelope",
            "building_shell": "envelope",
            "shell": "envelope",
            "other": "other",
        }
        return area_map.get(s, v)

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v):
        if v is None:
            return "low"
        s = str(v).strip().lower()
        sev_map = {
            "low": "low",
            "lo": "low",
            "l": "low",

            "med": "med",
            "mid": "med",
            "medium": "med",
            "moderate": "med",
            "m": "med",

            "high": "high",
            "hi": "high",
            "h": "high",
            "severe": "high",
        }
        return sev_map.get(s, v)


class AuditResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    findings: List[Finding] = Field(default_factory=list)


class Recommendation(BaseModel):
    action: str
    steps: List[str] = Field(default_factory=list)
    pct_kwh_reduction_min: float
    pct_kwh_reduction_max: float
    est_cost: float
    notes: Optional[str] = ""


class Recommendations(BaseModel):
    model_config = ConfigDict(extra="ignore")
    recommendations: List[Recommendation] = Field(default_factory=list)


class ImpactAction(BaseModel):
    action: str
    kWh_saved_per_month: float
    LKR_saved_per_month: float
    est_cost: float
    notes: Optional[str] = ""


class ImpactTotals(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kWh_saved_per_month: float
    LKR_saved_per_month: float


class ImpactPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    quick_wins: List[ImpactAction] = Field(default_factory=list)
    all_actions: List[ImpactAction] = Field(default_factory=list)
    totals: ImpactTotals
    plan_text: str

