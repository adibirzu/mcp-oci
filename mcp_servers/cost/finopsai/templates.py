from __future__ import annotations
from typing import Dict, Any

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "cost_by_compartment_daily": {"description": "Daily cost by compartment+service; forecast option.", "inputs": ["tenancy_ocid","time_start","time_end","compartment_depth","include_forecast","scope_compartment_ocid","include_children"], "output_schema": "CostByCompartment"},
    "cost_by_tag_key_value": {"description": "Cost by defined tag key=value; service split.", "inputs": ["tenancy_ocid","time_start","time_end","defined_tag_ns","defined_tag_key","defined_tag_value","scope_compartment_ocid","include_children"], "output_schema": "CostByTagOut"},
    "list_tag_defaults": {"description": "List tag default rules (tagging rules) for a compartment.", "inputs": ["compartment_id","include_children"], "output_schema": "TaggingRulesOut"},
    "cost_by_resource": {"description": "Cost by resource (ID/name) with optional filters.", "inputs": ["tenancy_ocid","time_start","time_end","top_n","scope_compartment_ocid","include_children","service_name","resource_ids","resource_name_contains"], "output_schema": "CostByResourceOut"},
    "cost_by_database": {"description": "Cost by database resources (Autonomous Database by default).", "inputs": ["tenancy_ocid","time_start","time_end","top_n","scope_compartment_ocid","include_children","service_name","database_ids","database_name_contains"], "output_schema": "CostByResourceOut"},
    "cost_by_pdb": {"description": "Cost by PDB name (best-effort).", "inputs": ["tenancy_ocid","time_start","time_end","top_n","scope_compartment_ocid","include_children","service_name","pdb_name_contains"], "output_schema": "CostByResourceOut"},
    "monthly_trend_forecast": {"description": "MoM trend with next-month forecast and optional budget variance.", "inputs": ["tenancy_ocid","months_back","budget_ocid"], "output_schema": "MonthlyTrend"},
    "service_cost_drilldown": {"description": "Top services by cost and their top compartments.", "inputs": ["tenancy_ocid","time_start","time_end","top_n","scope_compartment_ocid","include_children"], "output_schema": "ServiceDrilldown"},
    "anomaly_scan_focus": {"description": "Anomaly screen using FOCUS daily reports (z-score).", "inputs": ["tenancy_ocid","days_back","zscore_threshold"], "output_schema": "AnomalyScanOut"},
    "budget_status_and_actions": {"description": "Budgets, burn-rate & alert posture (with recursive option).", "inputs": ["compartment_ocid","include_children"], "output_schema": "BudgetStatusOut"},
    "schedule_report_create_or_list": {"description": "Ensure Usage API schedules exist; create or list.", "inputs": ["compartment_ocid","action","schedule_payload"], "output_schema": "SchedulesOut"},
    "tag_coverage_cost_weighted": {"description": "Tag completeness weighted by cost.", "inputs": ["tenancy_ocid","time_start","time_end","required_tags","scope_compartment_ocid","include_children"], "output_schema": "TagCoverageOut"},
    "compute_efficiency_snapshot": {"description": "Compute cost context + reservations note.", "inputs": ["tenancy_ocid","time_start","time_end","scope_compartment_ocid","include_children"], "output_schema": "ComputeEfficiencyOut"},
    "object_storage_costs_and_tiering": {"description": "Object Storage spend by bucket with lifecycle hints.", "inputs": ["tenancy_ocid","time_start","time_end","scope_compartment_ocid","include_children"], "output_schema": "ObjectStorageOut"},
    "focus_etl_healthcheck": {"description": "Verify FOCUS partitions presence and size.", "inputs": ["tenancy_ocid","days_back"], "output_schema": "FocusHealthOut"},
    "top_cost_spikes_explain": {"description": "Find DoD spikes and explain by service/compartment.", "inputs": ["tenancy_ocid","time_start","time_end","top_n","scope_compartment_ocid","include_children"], "output_schema": "SpikesOut"},
    "per_compartment_unit_cost": {"description": "Unit economics by compartment with per-service mapping.", "inputs": ["tenancy_ocid","time_start","time_end","unit","scope_compartment_ocid","include_children"], "output_schema": "UnitCostOut"},
    "forecast_vs_universal_credits": {"description": "Compare forecast vs Universal Credits.", "inputs": ["tenancy_ocid","months_ahead","credits_committed"], "output_schema": "ForecastCreditsOut"},
}
