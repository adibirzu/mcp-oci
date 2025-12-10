"""
Client adapters for MCP-OCI skills.

These adapters wrap the underlying server tools to provide a consistent
interface for skills. They handle connection management and data transformation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CostClientAdapter:
    """Adapter wrapping cost server tools for skills."""
    
    def __init__(self):
        """Initialize the cost client adapter."""
        self._cost_module = None
        self._load_cost_module()
    
    def _load_cost_module(self):
        """Lazily load cost server module."""
        try:
            from mcp_servers.cost import server as cost_server
            self._cost_module = cost_server
        except ImportError:
            logger.warning("Cost server module not available")
            self._cost_module = None
    
    def get_cost_summary(
        self,
        time_window: str = "7d",
        granularity: str = "DAILY",
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get cost summary for the specified time window."""
        if not self._cost_module:
            return {"error": "Cost module not available"}
        try:
            return self._cost_module.get_cost_summary(
                time_window=time_window,
                granularity=granularity,
                compartment_id=compartment_id
            )
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return {"error": str(e)}
    
    def get_usage_breakdown(
        self,
        service: Optional[str] = None,
        compartment_id: Optional[str] = None
    ) -> List[Dict]:
        """Get usage breakdown by service."""
        if not self._cost_module:
            return []
        try:
            return self._cost_module.get_usage_breakdown(
                service=service,
                compartment_id=compartment_id
            )
        except Exception as e:
            logger.error(f"Error getting usage breakdown: {e}")
            return []
    
    def cost_by_compartment_daily(
        self,
        tenancy_ocid: str,
        time_start: str,
        time_end: str,
        granularity: str = "DAILY",
        compartment_depth: int = 0,
        include_forecast: bool = True,
        scope_compartment_ocid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get daily cost by compartment."""
        if not self._cost_module:
            return {"error": "Cost module not available"}
        try:
            return self._cost_module.cost_by_compartment_daily(
                tenancy_ocid=tenancy_ocid,
                time_usage_started=time_start,
                time_usage_ended=time_end,
                granularity=granularity,
                compartment_depth=compartment_depth,
                include_forecast=include_forecast,
                scope_compartment_ocid=scope_compartment_ocid
            )
        except Exception as e:
            logger.error(f"Error getting daily costs: {e}")
            return {"error": str(e)}
    
    def service_cost_drilldown(
        self,
        tenancy_ocid: str,
        time_start: str,
        time_end: str,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """Get top services by cost."""
        if not self._cost_module:
            return {"error": "Cost module not available"}
        try:
            return self._cost_module.service_cost_drilldown(
                tenancy_ocid=tenancy_ocid,
                time_start=time_start,
                time_end=time_end,
                top_n=top_n
            )
        except Exception as e:
            logger.error(f"Error getting service drilldown: {e}")
            return {"error": str(e)}
    
    def monthly_trend_forecast(
        self,
        tenancy_ocid: str,
        months_back: int = 6,
        budget_ocid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get monthly trend with forecast."""
        if not self._cost_module:
            return {"error": "Cost module not available"}
        try:
            return self._cost_module.monthly_trend_forecast(
                tenancy_ocid=tenancy_ocid,
                months_back=months_back,
                budget_ocid=budget_ocid
            )
        except Exception as e:
            logger.error(f"Error getting monthly trend: {e}")
            return {"error": str(e)}
    
    def detect_cost_anomaly(
        self,
        series: List[float],
        method: str = "z_score",
        threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect cost anomalies in time series."""
        if not self._cost_module:
            return {"error": "Cost module not available"}
        try:
            return self._cost_module.detect_cost_anomaly(
                series=series,
                method=method,
                threshold=threshold
            )
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {"error": str(e)}
    
    def top_cost_spikes_explain(
        self,
        tenancy_ocid: str,
        time_start: str,
        time_end: str,
        top_n: int = 5
    ) -> Dict[str, Any]:
        """Find and explain top cost spikes."""
        if not self._cost_module:
            return {"error": "Cost module not available"}
        try:
            return self._cost_module.top_cost_spikes_explain(
                tenancy_ocid=tenancy_ocid,
                time_start=time_start,
                time_end=time_end,
                top_n=top_n
            )
        except Exception as e:
            logger.error(f"Error finding cost spikes: {e}")
            return {"error": str(e)}


class InventoryClientAdapter:
    """Adapter wrapping inventory server tools for skills."""
    
    def __init__(self):
        """Initialize the inventory client adapter."""
        self._inventory_module = None
        self._load_inventory_module()
    
    def _load_inventory_module(self):
        """Lazily load inventory server module."""
        try:
            from mcp_servers.inventory import server as inventory_server
            self._inventory_module = inventory_server
        except ImportError:
            logger.warning("Inventory server module not available")
            self._inventory_module = None
    
    def healthcheck(self) -> Dict[str, Any]:
        """Get server health status."""
        if not self._inventory_module:
            return {"error": "Inventory module not available"}
        try:
            return self._inventory_module.healthcheck()
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return {"error": str(e)}
    
    def get_tenancy_info(self) -> Dict[str, Any]:
        """Get tenancy information."""
        if not self._inventory_module:
            return {"error": "Inventory module not available"}
        try:
            return self._inventory_module.get_tenancy_info_inventory()
        except Exception as e:
            logger.error(f"Error getting tenancy info: {e}")
            return {"error": str(e)}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get local cache statistics."""
        if not self._inventory_module:
            return {"error": "Inventory module not available"}
        try:
            return self._inventory_module.get_cache_stats_inventory()
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    def run_showoci(
        self,
        profile: Optional[str] = None,
        regions: Optional[List[str]] = None,
        compartments: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        output_format: str = "text",
        diff_mode: bool = True,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run ShowOCI inventory report."""
        if not self._inventory_module:
            return {"error": "Inventory module not available"}
        try:
            return self._inventory_module.run_showoci(
                profile=profile,
                regions=regions,
                compartments=compartments,
                resource_types=resource_types,
                output_format=output_format,
                diff_mode=diff_mode,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error running showoci: {e}")
            return {"error": str(e)}
    
    def generate_compute_capacity_report(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None,
        include_metrics: bool = True,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Generate compute capacity report."""
        if not self._inventory_module:
            return {"error": "Inventory module not available"}
        try:
            return self._inventory_module.generate_compute_capacity_report(
                compartment_id=compartment_id,
                region=region,
                include_metrics=include_metrics,
                output_format=output_format
            )
        except Exception as e:
            logger.error(f"Error generating capacity report: {e}")
            return {"error": str(e)}
    
    def list_all_discovery(
        self,
        compartment_id: Optional[str] = None,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        limit_per_type: int = 25
    ) -> Dict[str, Any]:
        """Aggregate discovery of core resources."""
        if not self._inventory_module:
            return {"error": "Inventory module not available"}
        try:
            return self._inventory_module.list_all_discovery(
                compartment_id=compartment_id,
                profile=profile,
                region=region,
                limit_per_type=limit_per_type
            )
        except Exception as e:
            logger.error(f"Error in discovery: {e}")
            return {"error": str(e)}


class NetworkClientAdapter:
    """Adapter wrapping network server tools for skills."""
    
    def __init__(self):
        """Initialize the network client adapter."""
        self._network_module = None
        self._load_network_module()
    
    def _load_network_module(self):
        """Lazily load network server module."""
        try:
            from mcp_servers.network import server as network_server
            self._network_module = network_server
        except ImportError:
            logger.warning("Network server module not available")
            self._network_module = None
    
    def list_vcns(self, compartment_id: Optional[str] = None) -> List[Dict]:
        """List VCNs in a compartment."""
        if not self._network_module:
            return []
        try:
            return self._network_module.list_vcns(compartment_id=compartment_id)
        except Exception as e:
            logger.error(f"Error listing VCNs: {e}")
            return []
    
    def list_subnets(
        self,
        vcn_id: str,
        compartment_id: Optional[str] = None
    ) -> List[Dict]:
        """List subnets in a VCN."""
        if not self._network_module:
            return []
        try:
            return self._network_module.list_subnets(
                vcn_id=vcn_id,
                compartment_id=compartment_id
            )
        except Exception as e:
            logger.error(f"Error listing subnets: {e}")
            return []
    
    def summarize_public_endpoints(
        self,
        compartment_id: Optional[str] = None
    ) -> List[Dict]:
        """Summarize public endpoints."""
        if not self._network_module:
            return []
        try:
            return self._network_module.summarize_public_endpoints(
                compartment_id=compartment_id
            )
        except Exception as e:
            logger.error(f"Error summarizing endpoints: {e}")
            return []
    
    def create_vcn(
        self,
        display_name: str,
        cidr_block: str,
        compartment_id: Optional[str] = None,
        dns_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new VCN."""
        if not self._network_module:
            return {"error": "Network module not available"}
        try:
            return self._network_module.create_vcn(
                display_name=display_name,
                cidr_block=cidr_block,
                compartment_id=compartment_id,
                dns_label=dns_label
            )
        except Exception as e:
            logger.error(f"Error creating VCN: {e}")
            return {"error": str(e)}
    
    def create_subnet(
        self,
        vcn_id: str,
        display_name: str,
        cidr_block: str,
        availability_domain: Optional[str] = None,
        compartment_id: Optional[str] = None,
        dns_label: Optional[str] = None,
        prohibit_public_ip_on_vnic: bool = True
    ) -> Dict[str, Any]:
        """Create a new subnet."""
        if not self._network_module:
            return {"error": "Network module not available"}
        try:
            return self._network_module.create_subnet(
                vcn_id=vcn_id,
                display_name=display_name,
                cidr_block=cidr_block,
                availability_domain=availability_domain,
                compartment_id=compartment_id,
                dns_label=dns_label,
                prohibit_public_ip_on_vnic=prohibit_public_ip_on_vnic
            )
        except Exception as e:
            logger.error(f"Error creating subnet: {e}")
            return {"error": str(e)}
