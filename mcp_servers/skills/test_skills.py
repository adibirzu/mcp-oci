"""
Test suite for MCP-OCI Skills

These tests validate the skills layer functionality using mock adapters.
Run with: python -m pytest mcp_servers/skills/test_skills.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from .cost_analysis import CostAnalysisSkill
from .inventory_audit import InventoryAuditSkill
from .network_diagnostics import NetworkDiagnosticsSkill


class MockCostClientAdapter:
    """Mock adapter for cost client."""
    
    def monthly_trend_forecast(self, tenancy_ocid, months_back, budget_ocid=None):
        return {
            "data": {
                "series": [
                    {"month": "2025-01", "actual": 1000},
                    {"month": "2025-02", "actual": 1200},
                    {"month": "2025-03", "actual": 1100}
                ],
                "forecast": {"next_month": 1250, "currency": "USD"},
                "budget": None
            }
        }
    
    def top_cost_spikes_explain(self, tenancy_ocid, time_start, time_end, top_n):
        return {
            "data": {
                "spikes": [
                    {
                        "date": "2025-01-15",
                        "delta": 500,
                        "services": [{"service": "Compute", "cost": 300}],
                        "compartments": [{"name": "prod", "cost": 400}]
                    }
                ]
            }
        }
    
    def service_cost_drilldown(self, tenancy_ocid, time_start, time_end, top_n):
        return {
            "data": {
                "top": [
                    {"service": "Compute", "total": 5000, "compartments": [{"name": "prod", "cost": 3000}]},
                    {"service": "Database", "total": 3000, "compartments": [{"name": "prod", "cost": 2000}]},
                    {"service": "Networking", "total": 1000, "compartments": [{"name": "prod", "cost": 800}]}
                ]
            }
        }


class MockInventoryClientAdapter:
    """Mock adapter for inventory client."""
    
    def list_all_discovery(self, compartment_id=None, region=None, limit_per_type=50):
        return {
            "vcns": {"items": [{"id": "vcn1", "display_name": "VCN-1"}]},
            "subnets": {"items": [
                {"id": "subnet1", "display_name": "public", "prohibit_public_ip_on_vnic": False},
                {"id": "subnet2", "display_name": "private", "prohibit_public_ip_on_vnic": True}
            ]},
            "instances": {"items": [
                {"id": "inst1", "lifecycle_state": "RUNNING"},
                {"id": "inst2", "lifecycle_state": "STOPPED"}
            ]},
            "load_balancers": {"items": []}
        }
    
    def generate_compute_capacity_report(self, compartment_id=None, region=None, include_metrics=True, output_format="json"):
        return {
            "timestamp": datetime.now().isoformat(),
            "total_instances": 10,
            "instances_by_state": {"RUNNING": 7, "STOPPED": 3},
            "instances_by_shape": {"VM.Standard.E4.Flex": 6, "VM.Standard2.1": 4},
            "instances_by_ad": {"AD-1": 5, "AD-2": 5},
            "recommendations": []
        }
    
    def run_showoci(self, profile=None, regions=None, compartments=None, diff_mode=True, limit=None):
        return {
            "changes_detected": True,
            "diff": "+new instance\n-old instance"
        }


class MockNetworkClientAdapter:
    """Mock adapter for network client."""
    
    def list_vcns(self, compartment_id=None):
        return [
            {"id": "vcn1", "display_name": "VCN-Prod", "cidr_block": "10.0.0.0/16"},
            {"id": "vcn2", "display_name": "VCN-Dev", "cidr_block": "10.1.0.0/16"}
        ]
    
    def list_subnets(self, vcn_id, compartment_id=None):
        if vcn_id == "vcn1":
            return [
                {"id": "s1", "display_name": "public", "cidr_block": "10.0.1.0/24", "prohibit_public_ip_on_vnic": False},
                {"id": "s2", "display_name": "private", "cidr_block": "10.0.2.0/24", "prohibit_public_ip_on_vnic": True}
            ]
        else:
            return [
                {"id": "s3", "display_name": "public-only", "cidr_block": "10.1.1.0/24", "prohibit_public_ip_on_vnic": False}
            ]
    
    def summarize_public_endpoints(self, compartment_id=None):
        return [
            {"vcn": "VCN-Prod", "public_subnets": 1, "total_subnets": 2},
            {"vcn": "VCN-Dev", "public_subnets": 1, "total_subnets": 1}
        ]


class TestCostAnalysisSkill:
    """Tests for CostAnalysisSkill."""
    
    def test_analyze_cost_trend(self):
        """Test cost trend analysis."""
        skill = CostAnalysisSkill(client=MockCostClientAdapter())
        result = skill.analyze_cost_trend(
            tenancy_ocid="ocid1.tenancy.oc1..test",
            months_back=3
        )
        
        assert result["analysis_type"] == "cost_trend"
        assert "trend" in result
        assert result["trend"]["direction"] in ["increasing", "decreasing", "stable"]
        assert "recommendations" in result
        assert "summary" in result
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        skill = CostAnalysisSkill(client=MockCostClientAdapter())
        result = skill.detect_anomalies(
            tenancy_ocid="ocid1.tenancy.oc1..test",
            time_start="2025-01-01",
            time_end="2025-01-31"
        )
        
        assert result["analysis_type"] == "anomaly_detection"
        assert "total_anomalies" in result
        assert "anomalies" in result
        assert "severity_breakdown" in result
    
    def test_get_service_breakdown(self):
        """Test service breakdown."""
        skill = CostAnalysisSkill(client=MockCostClientAdapter())
        result = skill.get_service_breakdown(
            tenancy_ocid="ocid1.tenancy.oc1..test",
            time_start="2025-01-01",
            time_end="2025-01-31"
        )
        
        assert result["analysis_type"] == "service_breakdown"
        assert "services" in result
        assert "total_cost" in result
        assert "concentration_analysis" in result
    
    def test_optimization_potential_classification(self):
        """Test that services are classified by optimization potential."""
        skill = CostAnalysisSkill(client=MockCostClientAdapter())
        result = skill.get_service_breakdown(
            tenancy_ocid="ocid1.tenancy.oc1..test",
            time_start="2025-01-01",
            time_end="2025-01-31"
        )
        
        # Compute should be high potential
        compute_service = next(
            (s for s in result["services"] if "Compute" in s.get("service", "")),
            None
        )
        if compute_service:
            assert compute_service["optimization_potential"] == "high"


class TestInventoryAuditSkill:
    """Tests for InventoryAuditSkill."""
    
    def test_run_full_discovery(self):
        """Test full infrastructure discovery."""
        skill = InventoryAuditSkill(client=MockInventoryClientAdapter())
        result = skill.run_full_discovery()
        
        assert result["discovery_type"] == "full_infrastructure"
        assert "resource_summary" in result
        assert "total_resources" in result
        assert "health_assessment" in result
        assert "tagging_compliance" in result
    
    def test_generate_capacity_report(self):
        """Test capacity report generation."""
        skill = InventoryAuditSkill(client=MockInventoryClientAdapter())
        result = skill.generate_capacity_report()
        
        assert result["report_type"] == "capacity_planning"
        assert "utilization_analysis" in result
        assert "shape_analysis" in result
        assert "availability_analysis" in result
        assert "overall_assessment" in result
    
    def test_utilization_analysis(self):
        """Test utilization analysis calculations."""
        skill = InventoryAuditSkill(client=MockInventoryClientAdapter())
        result = skill.generate_capacity_report()
        
        utilization = result["utilization_analysis"]
        assert "total_instances" in utilization
        assert "running_instances" in utilization
        assert "active_rate" in utilization
        assert "idle_rate" in utilization
    
    def test_detect_changes(self):
        """Test change detection."""
        skill = InventoryAuditSkill(client=MockInventoryClientAdapter())
        result = skill.detect_changes()
        
        assert result["detection_type"] == "infrastructure_changes"
        assert "changes_detected" in result
        # When changes detected, should have analysis
        if result["changes_detected"]:
            assert "change_analysis" in result


class TestNetworkDiagnosticsSkill:
    """Tests for NetworkDiagnosticsSkill."""
    
    def test_analyze_topology(self):
        """Test network topology analysis."""
        skill = NetworkDiagnosticsSkill(client=MockNetworkClientAdapter())
        result = skill.analyze_topology()
        
        assert result["analysis_type"] == "network_topology"
        assert "topology" in result
        assert "total_vcns" in result["topology"]
        assert "total_subnets" in result["topology"]
        assert "summary" in result
    
    def test_assess_security(self):
        """Test security assessment."""
        skill = NetworkDiagnosticsSkill(client=MockNetworkClientAdapter())
        result = skill.assess_security()
        
        assert result["analysis_type"] == "security_assessment"
        assert "security_score" in result
        assert 0 <= result["security_score"] <= 100
        assert "status" in result
        assert "findings" in result
    
    def test_diagnose_connectivity(self):
        """Test connectivity diagnosis."""
        skill = NetworkDiagnosticsSkill(client=MockNetworkClientAdapter())
        result = skill.diagnose_connectivity()
        
        assert result["analysis_type"] == "connectivity_diagnosis"
        assert "overall_status" in result
        assert "diagnostics" in result
        assert "vcn_analysis" in result["diagnostics"]
    
    def test_cidr_size_calculation(self):
        """Test CIDR size calculation."""
        skill = NetworkDiagnosticsSkill(client=MockNetworkClientAdapter())
        
        # Test /16 network
        size = skill._calculate_cidr_size("10.0.0.0/16")
        assert size["prefix"] == 16
        assert size["total_ips"] == 65536
        
        # Test /24 network
        size = skill._calculate_cidr_size("10.0.1.0/24")
        assert size["prefix"] == 24
        assert size["total_ips"] == 256
    
    def test_public_only_vcn_detection(self):
        """Test detection of VCNs with only public subnets."""
        skill = NetworkDiagnosticsSkill(client=MockNetworkClientAdapter())
        result = skill.assess_security()
        
        # Should detect VCN-Dev as having only public subnets
        findings = result.get("findings", [])
        all_public_findings = [f for f in findings if f.get("type") == "all_public_network"]
        
        # VCN-Dev should trigger this finding
        assert len(all_public_findings) > 0


class TestSkillIntegration:
    """Integration tests for skill interactions."""
    
    def test_cost_and_inventory_correlation(self):
        """Test that cost and inventory skills can be used together."""
        cost_skill = CostAnalysisSkill(client=MockCostClientAdapter())
        inventory_skill = InventoryAuditSkill(client=MockInventoryClientAdapter())
        
        # Get cost breakdown
        cost_result = cost_skill.get_service_breakdown(
            tenancy_ocid="test",
            time_start="2025-01-01",
            time_end="2025-01-31"
        )
        
        # Get inventory
        inventory_result = inventory_skill.run_full_discovery()
        
        # Both should succeed
        assert "error" not in cost_result
        assert "error" not in inventory_result
        
        # Both should have data
        assert len(cost_result.get("services", [])) > 0
        assert inventory_result.get("total_resources", 0) > 0
    
    def test_network_and_inventory_correlation(self):
        """Test that network and inventory skills complement each other."""
        network_skill = NetworkDiagnosticsSkill(client=MockNetworkClientAdapter())
        inventory_skill = InventoryAuditSkill(client=MockInventoryClientAdapter())
        
        # Get network topology
        network_result = network_skill.analyze_topology()
        
        # Get inventory discovery
        inventory_result = inventory_skill.run_full_discovery()
        
        # Network should show VCN details
        assert network_result["topology"]["total_vcns"] > 0
        
        # Inventory should show VCN count too
        vcn_summary = next(
            (r for r in inventory_result.get("resource_summary", []) if r.get("type") == "VCN"),
            None
        )
        # (Mock may not have exact VCN count match, but should have data)
        assert vcn_summary is not None or inventory_result["total_resources"] > 0


class TestErrorHandling:
    """Tests for error handling in skills."""
    
    def test_cost_skill_handles_errors(self):
        """Test that cost skill handles adapter errors gracefully."""
        class ErrorAdapter:
            def monthly_trend_forecast(self, *args, **kwargs):
                return {"error": "API error"}
        
        skill = CostAnalysisSkill(client=ErrorAdapter())
        result = skill.analyze_cost_trend("test")
        
        assert "error" in result
    
    def test_inventory_skill_handles_errors(self):
        """Test that inventory skill handles adapter errors gracefully."""
        class ErrorAdapter:
            def list_all_discovery(self, *args, **kwargs):
                return {"error": "API error"}
        
        skill = InventoryAuditSkill(client=ErrorAdapter())
        result = skill.run_full_discovery()
        
        assert "error" in result
    
    def test_network_skill_handles_errors(self):
        """Test that network skill handles adapter errors gracefully."""
        class ErrorAdapter:
            def list_vcns(self, *args, **kwargs):
                return {"error": "API error"}
        
        skill = NetworkDiagnosticsSkill(client=ErrorAdapter())
        result = skill.analyze_topology()
        
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
