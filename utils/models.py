from __future__ import annotations
from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator

DisruptionLevel = Literal["none", "low", "medium", "high"]

class PolicyGoals(BaseModel):
    """
    Hard constraints / goals that steer recommendations and selection.
    All fields are optional so existing payloads remain valid.
    """
    model_config = ConfigDict(extra="ignore")

    target_budget_LKR: Optional[float] = Field(
        default=None, ge=0, description="Total CAPEX budget cap for all actions, in LKR."
    )
    payback_threshold_months: Optional[int] = Field(
        default=None, ge=0, description="Reject actions whose simple payback exceeds this many months."
    )
    co2_reduction_goal_pct: Optional[float] = Field(
        default=None, ge=0, le=100, description="Minimum % reduction of monthly CO₂ emissions to aim for."
    )
    max_disruption: Optional[DisruptionLevel] = Field(
        default="medium",
        description='Upper bound on disruption allowed: "none" < "low" < "medium" < "high".'
    )

    @field_validator("target_budget_LKR", "co2_reduction_goal_pct", mode="before")
    @classmethod
    def _none_if_empty(cls, v):
        if v in ("", None):
            return None
        return v

    @field_validator("max_disruption", mode="before")
    @classmethod
    def _normalize_disruption(cls, v):
        if v is None:
            return "medium"
        s = str(v).strip().lower()
        if s in {"none", "low", "medium", "high"}:
            return s
        return "medium"


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
    model_config = ConfigDict(extra="ignore")
    floor_area_m2: float = 0.0
    ac_units: List[ACUnit] = Field(default_factory=list)
    lighting: Lighting = Field(default_factory=Lighting)
    tariff_LKR_per_kWh: float = 0.0
    monthly_kWh: float = 0.0
    policy: Optional[PolicyGoals] = None


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
            "operations": "other",
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

    disruption: Optional[DisruptionLevel] = Field(default="medium", description="Estimated disruption level.")

    kwh_saved_per_month: Optional[float] = Field(default=None, ge=0)

    payback_months: Optional[float] = Field(default=None, ge=0)

    @field_validator("disruption", mode="before")
    @classmethod
    def _norm_disruption(cls, v):
        if v is None:
            return "medium"
        s = str(v).strip().lower()
        return s if s in {"none", "low", "medium", "high"} else "medium"


class Recommendations(BaseModel):
    model_config = ConfigDict(extra="ignore")
    recommendations: List[Recommendation] = Field(default_factory=list)
    policy_report: Optional[Dict[str, Any]] = None

class ImpactAction(BaseModel):
    action: str
    kWh_saved_per_month: float
    LKR_saved_per_month: float
    est_cost: float
    notes: Optional[str] = ""
    co2_kg_saved_per_month: float = Field(default=0.0, ge=0)
    disruption: DisruptionLevel = Field(default="medium")
    payback_months: Optional[float] = Field(default=None, ge=0)


class ImpactTotals(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kWh_saved_per_month: float
    LKR_saved_per_month: float
    co2_kg_saved_per_month: float = Field(default=0.0, ge=0)


class ImpactPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    quick_wins: List[ImpactAction] = Field(default_factory=list)
    all_actions: List[ImpactAction] = Field(default_factory=list)
    totals: ImpactTotals
    plan_text: str
    policy: Optional[PolicyGoals] = None

#Api Specific Related Models
class RawPayload(BaseModel):
    payload: Dict[str, Any]

class ComposeInput(BaseModel):
    normalized: NormalizedInput
    findings: AuditResult

class EstimateInput(BaseModel):
    normalized: NormalizedInput
    recommendations: Recommendations