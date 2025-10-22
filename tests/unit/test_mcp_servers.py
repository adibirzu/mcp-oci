from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest


class FakeCache:
    def __init__(self, payload: Any):
        self._payload = payload

    def get_or_refresh(self, **_: Any) -> Any:
        return self._payload


def test_compute_list_instances_uses_cached_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mcp_servers.compute import server as compute

    payload = [
        {
            "id": "ocid1.instance.oc1..example",
            "display_name": "demo-instance",
            "lifecycle_state": "RUNNING",
        }
    ]

    monkeypatch.setattr(compute, "get_cache", lambda: FakeCache(payload))
    monkeypatch.setattr(compute, "get_oci_config", lambda: {"region": "us-ashburn-1"})
    monkeypatch.setattr(
        compute, "get_compartment_id", lambda: "ocid1.compartment.oc1..example"
    )

    result = compute.list_instances()
    assert result == payload


def test_db_list_autonomous_databases(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.db import server as db

    payload = (
        [
            {
                "id": "ocid1.autonomousdatabase.oc1..example",
                "display_name": "adb-demo",
                "lifecycle_state": "AVAILABLE",
                "db_workload": "DW",
            }
        ],
        "opc-req-db",
    )

    monkeypatch.setattr(db, "get_cache", lambda: FakeCache(payload))
    monkeypatch.setattr(
        db,
        "get_oci_config",
        lambda: {"region": "us-ashburn-1", "tenancy": "ocid1.tenancy.oc1..example"},
    )
    monkeypatch.setattr(
        db, "get_compartment_id", lambda: "ocid1.compartment.oc1..example"
    )

    result = db.list_autonomous_databases()
    assert result and result[0]["display_name"] == "adb-demo"


def test_network_list_vcns(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.network import server as network

    payload = (
        [
            {
                "id": "ocid1.vcn.oc1..example",
                "display_name": "demo-vcn",
                "cidr_block": "10.0.0.0/16",
            }
        ],
        "opc-req-network",
    )

    monkeypatch.setattr(network, "get_cache", lambda: FakeCache(payload))
    monkeypatch.setattr(network, "get_oci_config", lambda: {"region": "us-ashburn-1"})
    monkeypatch.setattr(
        network, "get_compartment_id", lambda: "ocid1.compartment.oc1..example"
    )

    result = network.list_vcns()
    assert result and result[0]["display_name"] == "demo-vcn"


def test_security_list_compartments(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.security import server as security

    payload = [
        {
            "id": "ocid1.compartment.oc1..root",
            "name": "root",
            "description": "",
            "compartment_id": "ocid1.tenancy.oc1..example",
            "lifecycle_state": "ACTIVE",
        }
    ]

    monkeypatch.setattr(security, "get_cache", lambda: FakeCache(payload))
    monkeypatch.setattr(
        security, "_fetch_compartments", lambda *_: payload
    )  # defensive: cache miss

    result = security.list_compartments()
    assert result and result[0]["name"] == "root"


def test_cost_get_cost_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.cost import server as cost

    summary = (
        {
            "total_cost": 42.0,
            "currency": "USD",
            "time_period": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-07T00:00:00Z",
                "granularity": "DAILY",
            },
            "items_count": 3,
        },
        "opc-req-cost",
    )

    monkeypatch.setattr(cost, "get_cache", lambda: FakeCache(summary))

    result = cost.get_cost_summary()
    assert pytest.approx(result["total_cost"]) == 42.0
    assert result["currency"] == "USD"


def _stub_list_response(items: List[Dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(data=items, headers={"opc-request-id": "req"})


def test_blockstorage_list_volumes(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.blockstorage import server as blockstorage

    class FakeBlockstorageClient:
        def __init__(self) -> None:
            self.base_client = SimpleNamespace(
                endpoint="https://blockstorage.example.com"
            )

        def list_volumes(self, **_: Any) -> None:
            return None

    monkeypatch.setattr(
        blockstorage, "get_client", lambda *_, **__: FakeBlockstorageClient()
    )
    monkeypatch.setattr(
        blockstorage,
        "list_call_get_all_results",
        lambda *_, **__: _stub_list_response(
            [SimpleNamespace(id="ocid1.volume.oc1..example", display_name="demo-vol")]
        ),
    )
    monkeypatch.setattr(
        blockstorage, "get_compartment_id", lambda: "ocid1.compartment.oc1..example"
    )
    monkeypatch.setattr(
        blockstorage, "get_oci_config", lambda: {"region": "us-ashburn-1"}
    )

    result = blockstorage.list_volumes()
    assert result and result[0]["id"] == "ocid1.volume.oc1..example"


def test_loadbalancer_list_load_balancers(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.loadbalancer import server as loadbalancer

    class FakeLoadBalancerClient:
        def __init__(self) -> None:
            self.base_client = SimpleNamespace(endpoint="https://lb.example.com")

        def list_load_balancers(self, **_: Any) -> None:
            return None

    monkeypatch.setattr(
        loadbalancer, "get_client", lambda *_, **__: FakeLoadBalancerClient()
    )
    monkeypatch.setattr(
        loadbalancer,
        "list_call_get_all_results",
        lambda *_, **__: _stub_list_response(
            [
                SimpleNamespace(
                    id="ocid1.loadbalancer.oc1..example", display_name="demo-lb"
                )
            ]
        ),
    )
    monkeypatch.setattr(
        loadbalancer, "get_compartment_id", lambda: "ocid1.compartment.oc1..example"
    )
    monkeypatch.setattr(
        loadbalancer, "get_oci_config", lambda: {"region": "us-ashburn-1"}
    )

    result = loadbalancer.list_load_balancers()
    assert result and result[0]["id"] == "ocid1.loadbalancer.oc1..example"


def test_loganalytics_validate_query(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.loganalytics import server as loganalytics

    def fake_enhance(query: str) -> Dict[str, Any]:
        return {
            "original_query": query,
            "enhanced_query": query + " | head 10",
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": ["Appended head 10"],
            "timestamp": "2024-01-01T00:00:00Z",
        }

    fake_module = SimpleNamespace(enhance_log_analytics_query=fake_enhance)
    monkeypatch.setitem(
        sys.modules, "mcp_servers.loganalytics.query_enhancer", fake_module
    )

    result = loganalytics.validate_query("SEARCH * FROM logs")
    assert result["success"] is True
    assert result["validation_result"]["enhanced_query"].endswith("| head 10")


def test_inventory_list_streams_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.inventory import server as inventory
    import sys

    fake_module = SimpleNamespace(
        list_streams=lambda **_: {"items": [{"name": "demo-stream"}]}
    )
    monkeypatch.setitem(sys.modules, "mcp_oci_streaming.server", fake_module)
    monkeypatch.setattr(
        inventory,
        "get_oci_config",
        lambda **__: {"tenancy": "ocid1.tenancy.oc1..example"},
    )

    result = inventory.list_streams_inventory(limit=5)
    assert result["count"] == 1
    assert result["items"][0]["name"] == "demo-stream"


def test_observability_metrics_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.observability import server as observability

    monkeypatch.setattr(
        observability,
        "_RECENT_CALLS",
        [{"tool": "demo", "timestamp": "2024-01-01T00:00:00Z"}],
    )
    monkeypatch.setattr(observability.os, "getenv", lambda key, default=None: default)
    monkeypatch.setattr(
        observability.mcp_otel_enhancer,
        "get_server_capabilities",
        lambda: {"otel": True},
    )

    result = observability.get_observability_metrics_summary()
    assert result["success"] is True
    assert result["metrics_summary"]["total_operations"] == 1


def test_agents_list_agents_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_servers.agents import server as agents

    class FakeResponse:
        def __init__(self) -> None:
            self.ok = True
            self.status_code = 200
            self._json = {"items": [{"id": "agent1", "display_name": "Demo Agent"}]}
            self.headers = {"Content-Type": "application/json"}

        def json(self) -> Dict[str, Any]:
            return self._json

        @property
        def text(self) -> str:
            return json.dumps(self._json)

    monkeypatch.setattr(agents, "_mode", lambda: "proxy")
    monkeypatch.setattr(agents, "_admin_base", lambda: "http://localhost:9999/agents")
    monkeypatch.setattr(agents.requests, "get", lambda *_, **__: FakeResponse())

    result = agents.list_agents()
    assert result["items"][0]["display_name"] == "Demo Agent"
