"""
OCI Compute domain tools.

Provides compute instance management capabilities including listing,
getting details, and lifecycle actions (start/stop/restart).
"""
from __future__ import annotations

from .tools import register_compute_tools
from .models import (
    ListInstancesInput,
    GetInstanceInput,
    InstanceActionInput,
    GetInstanceMetricsInput,
    ResponseFormat,
    LifecycleState,
    InstanceSummary,
    ListInstancesOutput,
    InstanceActionOutput,
)
from .formatters import ComputeFormatter

__all__ = [
    # Registration function
    "register_compute_tools",
    
    # Input models
    "ListInstancesInput",
    "GetInstanceInput",
    "InstanceActionInput",
    "GetInstanceMetricsInput",
    
    # Enums
    "ResponseFormat",
    "LifecycleState",
    
    # Output models
    "InstanceSummary",
    "ListInstancesOutput",
    "InstanceActionOutput",
    
    # Formatter
    "ComputeFormatter",
]
