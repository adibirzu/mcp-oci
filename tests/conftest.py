"""
Pytest configuration and shared fixtures for OCI MCP Server tests.
"""
from __future__ import annotations

import os
import pytest
from typing import Any, Generator
from unittest.mock import MagicMock, patch

# Ensure test environment
os.environ.setdefault("OCI_PROFILE", "DEFAULT")
os.environ.setdefault("OCI_REGION", "us-ashburn-1")


@pytest.fixture
def mock_oci_config() -> dict[str, str]:
    """Mock OCI configuration."""
    return {
        "tenancy": "ocid1.tenancy.oc1..aaaaaaaexample",
        "user": "ocid1.user.oc1..aaaaaaaexample",
        "fingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99",
        "key_file": "/mock/path/to/key.pem",
        "region": "us-ashburn-1",
    }


@pytest.fixture
def mock_compartment_id() -> str:
    """Mock compartment OCID."""
    return "ocid1.compartment.oc1..aaaaaaaexample"


@pytest.fixture
def mock_tenancy_id() -> str:
    """Mock tenancy OCID."""
    return "ocid1.tenancy.oc1..aaaaaaaexample"


@pytest.fixture
def mock_instance_id() -> str:
    """Mock instance OCID."""
    return "ocid1.instance.oc1.iad.aaaaaaaexample"


@pytest.fixture
def mock_vcn_id() -> str:
    """Mock VCN OCID."""
    return "ocid1.vcn.oc1.iad.aaaaaaaexample"


@pytest.fixture
def mock_adb_id() -> str:
    """Mock Autonomous Database OCID."""
    return "ocid1.autonomousdatabase.oc1.iad.aaaaaaaexample"


@pytest.fixture
def mock_instance() -> dict[str, Any]:
    """Mock compute instance data."""
    return {
        "id": "ocid1.instance.oc1.iad.aaaaaaaexample",
        "display_name": "test-instance-01",
        "lifecycle_state": "RUNNING",
        "availability_domain": "AD-1",
        "compartment_id": "ocid1.compartment.oc1..aaaaaaaexample",
        "shape": "VM.Standard.E4.Flex",
        "shape_config": {
            "ocpus": 2,
            "memory_in_gbs": 16,
        },
        "time_created": "2024-01-15T10:30:00Z",
        "region": "us-ashburn-1",
        "fault_domain": "FAULT-DOMAIN-1",
        "source_details": {
            "source_type": "image",
            "image_id": "ocid1.image.oc1.iad.aaaaaaaexample",
        },
    }


@pytest.fixture
def mock_instances_list(mock_instance: dict) -> list[dict[str, Any]]:
    """Mock list of compute instances."""
    instances = [mock_instance.copy()]
    for i in range(2, 6):
        inst = mock_instance.copy()
        inst["id"] = f"ocid1.instance.oc1.iad.aaaaaaaexample{i}"
        inst["display_name"] = f"test-instance-0{i}"
        instances.append(inst)
    return instances


@pytest.fixture
def mock_vcn() -> dict[str, Any]:
    """Mock VCN data."""
    return {
        "id": "ocid1.vcn.oc1.iad.aaaaaaaexample",
        "display_name": "test-vcn",
        "cidr_block": "10.0.0.0/16",
        "lifecycle_state": "AVAILABLE",
        "compartment_id": "ocid1.compartment.oc1..aaaaaaaexample",
        "dns_label": "testvcn",
        "time_created": "2024-01-10T08:00:00Z",
    }


@pytest.fixture
def mock_subnet() -> dict[str, Any]:
    """Mock subnet data."""
    return {
        "id": "ocid1.subnet.oc1.iad.aaaaaaaexample",
        "display_name": "test-subnet",
        "cidr_block": "10.0.1.0/24",
        "lifecycle_state": "AVAILABLE",
        "compartment_id": "ocid1.compartment.oc1..aaaaaaaexample",
        "vcn_id": "ocid1.vcn.oc1.iad.aaaaaaaexample",
        "availability_domain": "AD-1",
        "prohibit_public_ip_on_vnic": False,
        "dns_label": "testsubnet",
    }


@pytest.fixture
def mock_adb() -> dict[str, Any]:
    """Mock Autonomous Database data."""
    return {
        "id": "ocid1.autonomousdatabase.oc1.iad.aaaaaaaexample",
        "display_name": "test-adb",
        "db_name": "TESTADB",
        "lifecycle_state": "AVAILABLE",
        "compartment_id": "ocid1.compartment.oc1..aaaaaaaexample",
        "cpu_core_count": 1,
        "data_storage_size_in_tbs": 1,
        "db_workload": "OLTP",
        "is_free_tier": False,
        "is_auto_scaling_enabled": True,
        "time_created": "2024-01-12T14:00:00Z",
    }


@pytest.fixture
def mock_cost_summary() -> dict[str, Any]:
    """Mock cost summary data."""
    return {
        "total_cost": 12450.67,
        "currency": "USD",
        "period_start": "2024-01-01T00:00:00Z",
        "period_end": "2024-01-31T23:59:59Z",
        "daily_average": 401.63,
        "by_service": [
            {"name": "Compute", "cost": 5230.00, "percentage": 42.0},
            {"name": "Object Storage", "cost": 3100.00, "percentage": 24.9},
            {"name": "Autonomous Database", "cost": 2450.00, "percentage": 19.7},
            {"name": "Block Storage", "cost": 870.67, "percentage": 7.0},
            {"name": "Other", "cost": 800.00, "percentage": 6.4},
        ],
    }


@pytest.fixture
def mock_metrics_data() -> list[dict[str, Any]]:
    """Mock metrics data points."""
    return [
        {"timestamp": "2024-01-15T10:00:00Z", "value": 25.5},
        {"timestamp": "2024-01-15T10:05:00Z", "value": 32.1},
        {"timestamp": "2024-01-15T10:10:00Z", "value": 28.7},
        {"timestamp": "2024-01-15T10:15:00Z", "value": 45.2},
        {"timestamp": "2024-01-15T10:20:00Z", "value": 38.9},
    ]


@pytest.fixture
def mock_oci_client_manager():
    """Mock OCIClientManager for testing."""
    with patch("mcp_server_oci.core.client.OCIClientManager") as mock:
        manager = MagicMock()
        manager.tenancy_id = "ocid1.tenancy.oc1..aaaaaaaexample"
        manager.region = "us-ashburn-1"
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_identity_client():
    """Mock OCI Identity Client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_compute_client(mock_instances_list):
    """Mock OCI Compute Client."""
    client = MagicMock()
    
    # Mock list_instances
    response = MagicMock()
    response.data = mock_instances_list
    client.list_instances.return_value = response
    
    return client


@pytest.fixture
def mock_virtual_network_client(mock_vcn, mock_subnet):
    """Mock OCI Virtual Network Client."""
    client = MagicMock()
    
    # Mock list_vcns
    vcn_response = MagicMock()
    vcn_response.data = [mock_vcn]
    client.list_vcns.return_value = vcn_response
    
    # Mock list_subnets
    subnet_response = MagicMock()
    subnet_response.data = [mock_subnet]
    client.list_subnets.return_value = subnet_response
    
    return client


@pytest.fixture
def mock_database_client(mock_adb):
    """Mock OCI Database Client."""
    client = MagicMock()
    
    # Mock list_autonomous_databases
    response = MagicMock()
    response.data = [mock_adb]
    client.list_autonomous_databases.return_value = response
    
    return client


@pytest.fixture
def mock_usage_api_client(mock_cost_summary):
    """Mock OCI Usage API Client."""
    client = MagicMock()
    
    # Mock request_summarized_usages
    response = MagicMock()
    response.data = mock_cost_summary
    client.request_summarized_usages.return_value = response
    
    return client


@pytest.fixture
def mock_monitoring_client(mock_metrics_data):
    """Mock OCI Monitoring Client."""
    client = MagicMock()
    
    # Mock summarize_metrics_data
    response = MagicMock()
    response.data = mock_metrics_data
    client.summarize_metrics_data.return_value = response
    
    return client


# Markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require OCI access)")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")


# Collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers based on test location
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
