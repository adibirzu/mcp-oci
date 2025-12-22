from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Literal

class Window(BaseModel):
    start: str
    end: str

class CostByCompartmentRow(BaseModel):
    date: str
    compartment: str
    service: str
    cost: float

class CostByCompartment(BaseModel):
    window: Window
    currency: str
    rows: List[CostByCompartmentRow]
    forecast: Optional[dict] = None

class TagSpec(BaseModel):
    ns: str
    key: str
    value: Optional[str] = None

class CostByTagOut(BaseModel):
    tag: TagSpec
    currency: str
    services: List[dict]
    total: float

class MonthlyPoint(BaseModel):
    month: str
    actual: float

class MonthlyTrend(BaseModel):
    series: List[MonthlyPoint]
    forecast: dict
    budget: Optional[dict] = None

class ServiceCompartmentEntry(BaseModel):
    name: str
    cost: float

class TopService(BaseModel):
    service: str
    total: float
    compartments: List[ServiceCompartmentEntry]

class ServiceDrilldown(BaseModel):
    window: Window
    top: List[TopService]

class AnomalyDay(BaseModel):
    date: str
    total: float
    zscore: float
    is_anomaly: bool

class AnomalyScanOut(BaseModel):
    days: List[AnomalyDay]
    suspects: List[dict]

class BudgetAlert(BaseModel):
    threshold: float
    ruleType: Literal["FORECAST", "ACTUAL"]

class BudgetEntry(BaseModel):
    name: str
    ocid: str
    amount: float
    period: Literal["MONTHLY", "CUSTOM"]
    spendToDate: float
    projected: float
    alerts: List[BudgetAlert]

class BudgetStatusOut(BaseModel):
    budgets: List[dict]  # Simplified to dict since BudgetEntry may not match actual data
    compartment_id: Optional[str] = None
    recursive_children: bool = False

class ScheduleEntry(BaseModel):
    id: str
    name: str
    destination: Literal["OBJECT_STORAGE", "EMAIL"]
    frequency: Literal["DAILY", "WEEKLY", "MONTHLY"]

class SchedulesOut(BaseModel):
    action: Literal["LIST", "CREATE"]
    schedules: List[ScheduleEntry]

class TagCoverageOut(BaseModel):
    required: List[dict]
    coverage: dict
    recommendations: List[str]

class ComputeEfficiencyOut(BaseModel):
    window: Window
    computeSpend: float
    notes: List[str]
    advice: List[dict]

class BucketCost(BaseModel):
    name: str
    cost: float
    hint: str

class ObjectStorageOut(BaseModel):
    buckets: List[BucketCost]

class FocusHealthDay(BaseModel):
    date: str
    present: bool
    sizeBytes: int

class FocusHealthOut(BaseModel):
    days: List[FocusHealthDay]
    gaps: List[str]

class SpikeEntry(BaseModel):
    date: str
    delta: float
    services: List[dict]
    compartments: List[dict]

class SpikesOut(BaseModel):
    spikes: List[SpikeEntry]

class UnitCostRow(BaseModel):
    compartment: str
    cost: float
    quantity: float
    unitCost: float

class UnitCostOut(BaseModel):
    unit: Literal["OCPU_HOUR", "GB_MONTH"]
    rows: List[UnitCostRow]

class ForecastCreditsOut(BaseModel):
    forecast: dict
    credits: dict
    risk: Literal["UNDER", "OVER", "NEUTRAL"]
    notes: List[str]

class ResourceCostRow(BaseModel):
    resourceId: str
    resourceName: str
    service: str
    compartment: str
    cost: float

class CostByResourceOut(BaseModel):
    window: Window
    currency: str
    filters: dict
    rows: List[ResourceCostRow]

class TagDefaultRule(BaseModel):
    id: Optional[str] = None
    compartmentId: Optional[str] = None
    tagNamespaceId: Optional[str] = None
    tagDefinitionId: Optional[str] = None
    tagNamespaceName: Optional[str] = None
    tagName: Optional[str] = None
    value: Optional[str] = None
    lifecycleState: Optional[str] = None

class TaggingRulesOut(BaseModel):
    rules: List[TagDefaultRule]
