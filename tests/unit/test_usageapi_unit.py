import os
import sys
import types
from typing import Any


sys.path.insert(0, os.path.abspath("src"))


def _fake_oci_module():
    oci = types.SimpleNamespace()

    # usage_api models
    class Filter:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class RequestSummarizedUsagesDetails:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    usage_models = types.SimpleNamespace(
        Filter=Filter, RequestSummarizedUsagesDetails=RequestSummarizedUsagesDetails
    )
    usage_api = types.SimpleNamespace(models=usage_models)
    oci.usage_api = usage_api

    # resource_search models
    class StructuredSearchDetails:
        def __init__(self, query: str, **kwargs):
            self.query = query
            self.__dict__.update(kwargs)

    rs_models = types.SimpleNamespace(StructuredSearchDetails=StructuredSearchDetails)
    # Provide a placeholder ResourceSearchClient attribute to satisfy attribute access
    oci.resource_search = types.SimpleNamespace(
        models=rs_models, ResourceSearchClient=object
    )
    return oci


def test_request_summarized_usages_injects_compartment_from_name(monkeypatch):
    import mcp_oci_usageapi.server as srv

    # Fake oci models + client
    monkeypatch.setattr(srv, "oci", _fake_oci_module(), raising=True)

    captured: dict[str, Any] = {}

    class _Resp:
        def __init__(self):
            self.data = types.SimpleNamespace(items=[])

    class _Client:
        def request_summarized_usages(self, request_summarized_usages_details):  # type: ignore
            captured["details"] = request_summarized_usages_details
            return _Resp()

    monkeypatch.setattr(
        srv, "create_client", lambda profile=None, region=None: _Client()
    )
    # Resolve name to OCID
    monkeypatch.setattr(
        srv,
        "_resolve_compartment_name_to_id",
        lambda name, profile=None, region=None: "ocid1.compartment.oc1..abc",
    )

    # Ensure _build_filter returns an object with a dimensions attribute
    monkeypatch.setattr(
        srv,
        "_build_filter",
        lambda dimensions, tags: types.SimpleNamespace(
            dimensions=dimensions, tags=tags
        ),
    )

    out = srv.request_summarized_usages(
        tenant_id="ocid1.tenancy..xyz",
        time_usage_started="2025-01-01T00:00:00Z",
        time_usage_ended="2025-01-31T00:00:00Z",
        granularity="DAILY",
        query_type="COST",
        group_by=["service"],
        compartment_name="MyComp",
    )
    assert "items" in out
    det = captured["details"]
    # dimensions should contain injected compartmentId
    dims = getattr(det, "filter", types.SimpleNamespace()).__dict__.get(
        "dimensions", {}
    )
    assert dims.get("compartmentId") == "ocid1.compartment.oc1..abc"


def test_count_instances_paginates(monkeypatch):
    import mcp_oci_usageapi.server as srv

    monkeypatch.setattr(srv, "oci", _fake_oci_module(), raising=True)

    class _Resp:
        def __init__(self, items, nextp=None):
            self.data = types.SimpleNamespace(items=items)
            self.opc_next_page = nextp

    class _RSClient:
        def __init__(self):
            self.calls = 0

        def search_resources(self, **kwargs):
            # Return two pages: 2 items then 1 item
            self.calls += 1
            if self.calls == 1:
                return _Resp(
                    [
                        types.SimpleNamespace(resource_type="instance"),
                        types.SimpleNamespace(resource_type="instance"),
                    ],
                    nextp="p2",
                )
            return _Resp([types.SimpleNamespace(resource_type="instance")], nextp=None)

    monkeypatch.setattr(srv, "make_client", lambda *a, **k: _RSClient())

    out = srv.count_instances(
        compartment_id="ocid1.compartment..root", include_subtree=True
    )
    assert out["count"] == 3
    assert out["resource"] == "instance"


def test_correlate_costs_and_resources(monkeypatch):
    import mcp_oci_usageapi.server as srv

    monkeypatch.setattr(srv, "oci", _fake_oci_module(), raising=True)

    # Fake cost_by_service to avoid touching Usage API
    monkeypatch.setattr(
        srv,
        "cost_by_service",
        lambda tenant_id, days, granularity, profile=None, region=None: {
            "items": [{"service": "Compute", "cost": 12.3}]
        },
    )

    class _Resp:
        def __init__(self, items, nextp=None):
            self.data = types.SimpleNamespace(items=items)
            self.opc_next_page = nextp

    # Resource search returns mix of types
    class _RSClient:
        def search_resources(self, **kwargs):
            return _Resp(
                [
                    types.SimpleNamespace(resource_type="instance"),
                    types.SimpleNamespace(resource_type="volume"),
                    types.SimpleNamespace(resource_type="instance"),
                ],
                nextp=None,
            )

    monkeypatch.setattr(srv, "make_client", lambda *a, **k: _RSClient())

    out = srv.correlate_costs_and_resources(
        tenant_id="ocid1.tenancy..xyz",
        days=3,
        compartment_id="ocid1.compartment..root",
        include_subtree=True,
    )
    assert isinstance(out.get("cost_by_service"), list)
    assert out["resource_counts"].get("instance") == 2
    assert out["resource_counts"].get("volume") == 1
