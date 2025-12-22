import os
import logging
from typing import Dict, Optional, List
from fastmcp import FastMCP
from fastmcp.tools import Tool
import oci
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from mcp_oci_common.otel import trace
from oci.pagination import list_call_get_all_results
from mcp_oci_common import get_oci_config, get_compartment_id, add_oci_call_attributes, allow_mutations, validate_and_log_tools
from mcp_oci_common.session import get_client
from mcp_oci_common.cache import get_cache
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
import json

# Load repo-local .env.local so OCI/OTEL config is applied consistently.
try:
    from pathlib import Path
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(_repo_root / ".env.local")
except Exception:
    pass

# Set up tracing with proper Resource
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-network")
init_tracing(service_name="oci-mcp-network")
init_metrics()
tracer = trace.get_tracer("oci-mcp-network")

# Shared HTTP session with connection pooling and retries for OCI REST calls
_HTTP_SESSION = None

def _get_http_session():
    global _HTTP_SESSION
    if _HTTP_SESSION is not None:
        return _HTTP_SESSION
    try:
        pool = int(os.getenv("NET_HTTP_POOL", "16"))
        retries = int(os.getenv("NET_HTTP_RETRIES", "3"))
        backoff = float(os.getenv("NET_HTTP_BACKOFF", "0.2"))
        retry = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "PATCH"])
        )
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=pool, pool_maxsize=pool, max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _HTTP_SESSION = session
        return session
    except Exception:
        _HTTP_SESSION = requests.Session()
        return _HTTP_SESSION

# Logging setup
logging.basicConfig(level=logging.INFO if os.getenv('DEBUG') else logging.WARNING)
logger = logging.getLogger(__name__)


def _fetch_vcns(compartment_id: Optional[str] = None):
    compartment = compartment_id or get_compartment_id()
    config = get_oci_config()
    vn_client = get_client(oci.core.VirtualNetworkClient, region=config.get("region"))
    try:
        endpoint = getattr(vn_client.base_client, "endpoint", "")
    except Exception:
        endpoint = ""
    add_oci_call_attributes(
        None,  # No span in internal fetch
        oci_service="VirtualNetwork",
        oci_operation="ListVcns",
        region=config.get("region"),
        endpoint=endpoint,
    )
    response = list_call_get_all_results(vn_client.list_vcns, compartment_id=compartment)
    req_id = response.headers.get("opc-request-id")
    vcns = response.data
    return [{'display_name': vcn.display_name, 'id': vcn.id, 'cidr_block': getattr(vcn, 'cidr_block', '')} for vcn in vcns], req_id

def list_vcns(compartment_id: Optional[str] = None) -> List[Dict]:
    with tool_span(tracer, "list_vcns", mcp_server="oci-mcp-network") as span:
        compartment = compartment_id or get_compartment_id()
        cache = get_cache()
        params = {'compartment_id': compartment}
        try:
            result = cache.get_or_refresh(
                server_name="oci-mcp-network",
                operation="list_vcns",
                params=params,
                fetch_func=lambda: _fetch_vcns(compartment_id),
                ttl_seconds=600,
                force_refresh=False
            )
            # Handle None result from cache (fetch failed or empty cache)
            if result is None:
                logging.warning("Cache returned None for list_vcns - fetch may have failed")
                return []
            vcns, req_id = result
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            span.set_attribute("vcns.count", len(vcns))
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            return vcns
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing VCNs: {e}")
            span.record_exception(e)
            return []
        except (TypeError, ValueError) as e:
            logging.error(f"Error unpacking cache result for list_vcns: {e}")
            span.record_exception(e)
            return []

def _fetch_subnets(vcn_id: str, compartment_id: Optional[str] = None):
    compartment = compartment_id or get_compartment_id()
    config = get_oci_config()
    vn_client = get_client(oci.core.VirtualNetworkClient, region=config.get("region"))
    try:
        endpoint = getattr(vn_client.base_client, "endpoint", "")
    except Exception:
        endpoint = ""
    add_oci_call_attributes(
        None,  # No span in internal fetch
        oci_service="VirtualNetwork",
        oci_operation="ListSubnets",
        region=config.get("region"),
        endpoint=endpoint,
    )
    response = list_call_get_all_results(vn_client.list_subnets, compartment_id=compartment, vcn_id=vcn_id)
    req_id = response.headers.get("opc-request-id")
    subnets = response.data
    return [{'display_name': subnet.display_name, 'id': subnet.id, 'cidr_block': subnet.cidr_block, 'vcn_id': vcn_id} for subnet in subnets], req_id

def list_subnets(vcn_id: str, compartment_id: Optional[str] = None) -> List[Dict]:
    with tool_span(tracer, "list_subnets", mcp_server="oci-mcp-network") as span:
        compartment = compartment_id or get_compartment_id()
        cache = get_cache()
        params = {'vcn_id': vcn_id, 'compartment_id': compartment}
        try:
            result = cache.get_or_refresh(
                server_name="oci-mcp-network",
                operation="list_subnets",
                params=params,
                fetch_func=lambda: _fetch_subnets(vcn_id, compartment_id),
                ttl_seconds=600,
                force_refresh=False
            )
            # Handle None result from cache (fetch failed or empty cache)
            if result is None:
                logging.warning("Cache returned None for list_subnets - fetch may have failed")
                return []
            subnets, req_id = result
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            span.set_attribute("subnets.count", len(subnets))
            span.set_attribute("vcn_id", vcn_id)
            if compartment_id:
                span.set_attribute("compartment_id", compartment_id)
            return subnets
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error listing subnets: {e}")
            span.record_exception(e)
            return []
        except (TypeError, ValueError) as e:
            logging.error(f"Error unpacking cache result for list_subnets: {e}")
            span.record_exception(e)
            return []

def create_vcn(
    display_name: str,
    cidr_block: str,
    compartment_id: Optional[str] = None,
    dns_label: Optional[str] = None
) -> Dict:
    with tool_span(tracer, "create_vcn", mcp_server="oci-mcp-network") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = make_client(oci.core.VirtualNetworkClient)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="CreateVcn",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create VCN details
        create_vcn_details = oci.core.models.CreateVcnDetails(
            compartment_id=compartment,
            display_name=display_name,
            cidr_block=cidr_block
        )
        if dns_label:
            create_vcn_details.dns_label = dns_label

        try:
            response = vn_client.create_vcn(create_vcn_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            vcn = response.data
            return {
                'id': vcn.id,
                'display_name': vcn.display_name,
                'cidr_block': getattr(vcn, 'cidr_block', ''),
                'dns_label': getattr(vcn, 'dns_label', ''),
                'lifecycle_state': getattr(vcn, 'lifecycle_state', ''),
                'time_created': getattr(vcn, 'time_created', '').isoformat() if hasattr(vcn, 'time_created') and vcn.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating VCN: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def create_subnet(
    vcn_id: str,
    display_name: str,
    cidr_block: str,
    availability_domain: Optional[str] = None,
    compartment_id: Optional[str] = None,
    dns_label: Optional[str] = None,
    prohibit_public_ip_on_vnic: bool = True
) -> Dict:
    with tool_span(tracer, "create_subnet", mcp_server="oci-mcp-network") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}

        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = make_client(oci.core.VirtualNetworkClient)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="CreateSubnet",
            region=config.get("region"),
            endpoint=endpoint,
        )

        # Create subnet details
        create_subnet_details = oci.core.models.CreateSubnetDetails(
            compartment_id=compartment,
            vcn_id=vcn_id,
            display_name=display_name,
            cidr_block=cidr_block,
            prohibit_public_ip_on_vnic=prohibit_public_ip_on_vnic
        )
        if availability_domain:
            create_subnet_details.availability_domain = availability_domain
        if dns_label:
            create_subnet_details.dns_label = dns_label

        try:
            response = vn_client.create_subnet(create_subnet_details)
            req_id = getattr(response, "headers", {}).get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            subnet = response.data
            return {
                'id': subnet.id,
                'display_name': subnet.display_name,
                'vcn_id': subnet.vcn_id,
                'cidr_block': subnet.cidr_block,
                'availability_domain': getattr(subnet, 'availability_domain', ''),
                'dns_label': getattr(subnet, 'dns_label', ''),
                'prohibit_public_ip_on_vnic': getattr(subnet, 'prohibit_public_ip_on_vnic', True),
                'lifecycle_state': getattr(subnet, 'lifecycle_state', ''),
                'time_created': getattr(subnet, 'time_created', '').isoformat() if hasattr(subnet, 'time_created') and subnet.time_created else ''
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating subnet: {e}")
            span.record_exception(e)
            return {'error': str(e)}

def summarize_public_endpoints(compartment_id: Optional[str] = None) -> List[Dict]:
    with tool_span(tracer, "summarize_public_endpoints", mcp_server="oci-mcp-network") as span:
        compartment = compartment_id or get_compartment_id()
        config = get_oci_config()
        vn_client = get_client(oci.core.VirtualNetworkClient, region=config.get("region"))
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="ListVcns",
            region=config.get("region"),
            endpoint=endpoint,
        )
        try:
            response = list_call_get_all_results(vn_client.list_vcns, compartment_id=compartment)
            req_id = response.headers.get("opc-request-id")
            if req_id:
                span.set_attribute("oci.request_id", req_id)
            vcns = response.data
            public_endpoints = []
            for vcn in vcns:
                subnets_response = list_call_get_all_results(vn_client.list_subnets, compartment_id=compartment, vcn_id=vcn.id)
                subnets = subnets_response.data
                public_subnets = [s for s in subnets if not s.prohibit_public_ip_on_vnic]
                if public_subnets:
                    public_endpoints.append({
                        'vcn': vcn.display_name,
                        'vcn_id': vcn.id,
                        'public_subnets': len(public_subnets),
                        'total_subnets': len(subnets)
                    })
            span.set_attribute("public_endpoints.count", len(public_endpoints))
            return public_endpoints
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error summarizing public endpoints: {e}")
            span.record_exception(e)
            return []

def create_vcn_with_subnets(
    display_name: str,
    cidr_block: str,
    public_subnet_cidr: str,
    private_subnet_cidr: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    dns_label: Optional[str] = None,
    public_subnet_dns_label: Optional[str] = None,
    private_subnet_dns_label: Optional[str] = None,
    prohibit_public_ip_on_public_subnet: bool = False,
    prohibit_public_ip_on_private_subnet: bool = True
) -> Dict:
    """
    Orchestrates creation of a VCN with:
      - Internet Gateway
      - NAT Gateway
      - Public Route Table (0.0.0.0/0 -> IGW)
      - Private Route Table (0.0.0.0/0 -> NAT)
      - Public Subnet (allows public IPs, attached to public RT)
      - Private Subnet (no public IPs, attached to private RT)
    Returns a summary with OCIDs for all created resources.
    """
    with tool_span(tracer, "create_vcn_with_subnets", mcp_server="oci-mcp-network") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        compartment = compartment_id or get_compartment_id()
        if not compartment:
            return {'error': 'Compartment OCID not provided and COMPARTMENT_OCID is not set'}
        # Determine region to use
        cfg = get_oci_config()
        used_region = region or cfg.get("region")
        # Create client pinned to region
        vn_client = get_client(oci.core.VirtualNetworkClient, region=used_region)
        try:
            endpoint = getattr(vn_client.base_client, "endpoint", "")
        except Exception:
            endpoint = ""
        add_oci_call_attributes(
            span,
            oci_service="VirtualNetwork",
            oci_operation="CreateVcnWithSubnets",
            region=used_region,
            endpoint=endpoint,
        )

        created: Dict[str, Dict] = {}
        req_ids: List[str] = []
        try:
            # 1) VCN
            vcn_details = oci.core.models.CreateVcnDetails(
                compartment_id=compartment,
                display_name=display_name,
                cidr_block=cidr_block
            )
            if dns_label:
                vcn_details.dns_label = dns_label
            vcn_resp = vn_client.create_vcn(vcn_details)
            vcn = vcn_resp.data
            created["vcn"] = {
                "id": vcn.id,
                "display_name": vcn.display_name,
                "cidr_block": getattr(vcn, "cidr_block", ""),
                "dns_label": getattr(vcn, "dns_label", None),
            }
            rid = getattr(vcn_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            # 2) Internet Gateway
            igw_name = f"{display_name}-igw"
            igw_details = oci.core.models.CreateInternetGatewayDetails(
                compartment_id=compartment,
                vcn_id=vcn.id,
                display_name=igw_name,
                is_enabled=True
            )
            igw_resp = vn_client.create_internet_gateway(igw_details)
            igw = igw_resp.data
            created["internet_gateway"] = {"id": igw.id, "display_name": igw.display_name}
            rid = getattr(igw_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            # 3) NAT Gateway
            nat_name = f"{display_name}-nat"
            nat_details = oci.core.models.CreateNatGatewayDetails(
                compartment_id=compartment,
                vcn_id=vcn.id,
                display_name=nat_name
            )
            nat_resp = vn_client.create_nat_gateway(nat_details)
            nat = nat_resp.data
            created["nat_gateway"] = {"id": nat.id, "display_name": nat.display_name}
            rid = getattr(nat_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            # 4) Route Tables
            # Public RT -> IGW
            prt_name = f"{display_name}-public-rt"
            prt_details = oci.core.models.CreateRouteTableDetails(
                compartment_id=compartment,
                vcn_id=vcn.id,
                display_name=prt_name,
                route_rules=[
                    oci.core.models.RouteRule(
                        destination="0.0.0.0/0",
                        network_entity_id=igw.id,
                        description="All traffic to Internet via IGW"
                    )
                ]
            )
            prt_resp = vn_client.create_route_table(prt_details)
            public_rt = prt_resp.data
            created.setdefault("route_tables", {})["public"] = {
                "id": public_rt.id,
                "display_name": public_rt.display_name
            }
            rid = getattr(prt_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            # Private RT -> NAT
            privrt_name = f"{display_name}-private-rt"
            privrt_details = oci.core.models.CreateRouteTableDetails(
                compartment_id=compartment,
                vcn_id=vcn.id,
                display_name=privrt_name,
                route_rules=[
                    oci.core.models.RouteRule(
                        destination="0.0.0.0/0",
                        network_entity_id=nat.id,
                        description="All egress via NAT"
                    )
                ]
            )
            privrt_resp = vn_client.create_route_table(privrt_details)
            private_rt = privrt_resp.data
            created.setdefault("route_tables", {})["private"] = {
                "id": private_rt.id,
                "display_name": private_rt.display_name
            }
            rid = getattr(privrt_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            # 5) Public Subnet
            pub_subnet_name = f"{display_name}-public-subnet"
            pub_subnet_details = oci.core.models.CreateSubnetDetails(
                compartment_id=compartment,
                vcn_id=vcn.id,
                display_name=pub_subnet_name,
                cidr_block=public_subnet_cidr,
                prohibit_public_ip_on_vnic=prohibit_public_ip_on_public_subnet,
                route_table_id=public_rt.id
            )
            if public_subnet_dns_label:
                pub_subnet_details.dns_label = public_subnet_dns_label
            pubsub_resp = vn_client.create_subnet(pub_subnet_details)
            pub_subnet = pubsub_resp.data
            created.setdefault("subnets", {})["public"] = {
                "id": pub_subnet.id,
                "display_name": pub_subnet.display_name,
                "cidr_block": pub_subnet.cidr_block,
                "dns_label": getattr(pub_subnet, "dns_label", None),
                "prohibit_public_ip_on_vnic": getattr(pub_subnet, "prohibit_public_ip_on_vnic", False)
            }
            rid = getattr(pubsub_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            # 6) Private Subnet
            priv_subnet_name = f"{display_name}-private-subnet"
            priv_subnet_details = oci.core.models.CreateSubnetDetails(
                compartment_id=compartment,
                vcn_id=vcn.id,
                display_name=priv_subnet_name,
                cidr_block=private_subnet_cidr,
                prohibit_public_ip_on_vnic=prohibit_public_ip_on_private_subnet,
                route_table_id=private_rt.id
            )
            if private_subnet_dns_label:
                priv_subnet_details.dns_label = private_subnet_dns_label
            privsub_resp = vn_client.create_subnet(priv_subnet_details)
            priv_subnet = privsub_resp.data
            created.setdefault("subnets", {})["private"] = {
                "id": priv_subnet.id,
                "display_name": priv_subnet.display_name,
                "cidr_block": priv_subnet.cidr_block,
                "dns_label": getattr(priv_subnet, "dns_label", None),
                "prohibit_public_ip_on_vnic": getattr(priv_subnet, "prohibit_public_ip_on_vnic", True)
            }
            rid = getattr(privsub_resp, "headers", {}).get("opc-request-id")
            if rid:
                req_ids.append(rid)

            if req_ids:
                # attach the last request id as the span attribute; keep all in output
                span.set_attribute("oci.request_id", req_ids[-1])

            return {
                "region": used_region,
                "compartment_id": compartment,
                **created,
                "request_ids": req_ids
            }
        except oci.exceptions.ServiceError as e:
            logging.error(f"Error creating VCN with subnets: {e}")
            span.record_exception(e)
            result = {"error": str(e), "region": used_region, "compartment_id": compartment}
            if created:
                result["partial"] = created
            return result

def create_vcn_with_subnets_rest(
    display_name: str,
    cidr_block: str,
    public_subnet_cidr: str,
    private_subnet_cidr: str,
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    dns_label: Optional[str] = None,
    public_subnet_dns_label: Optional[str] = None,
    private_subnet_dns_label: Optional[str] = None,
    prohibit_public_ip_on_public_subnet: bool = False,
    prohibit_public_ip_on_private_subnet: bool = True
) -> Dict:
    """
    Create a VCN with public/private subnets using OCI REST API (signed HTTP), not the Python SDK.
    """
    with tool_span(tracer, "create_vcn_with_subnets_rest", mcp_server="oci-mcp-network") as span:
        if not allow_mutations():
            return {'error': 'Mutations not allowed (set ALLOW_MUTATIONS=true)'}
        comp = compartment_id or get_compartment_id()
        if not comp:
            return {'error': 'Compartment OCID not provided and COMPARTMENT_OCID is not set'}

        cfg = get_oci_config()
        used_region = region or cfg.get("region")
        base_url = f"https://iaas.{used_region}.oraclecloud.com/20160918"

        # Build a signer for REST calls
        signer = cfg.get("signer")
        if signer is None:
            try:
                from oci.signer import Signer
                signer = Signer(
                    tenancy=cfg["tenancy"],
                    user=cfg["user"],
                    fingerprint=cfg["fingerprint"],
                    private_key_file_location=cfg["key_file"],
                    pass_phrase=cfg.get("pass_phrase") or None,
                )
            except Exception as e:
                logging.error("Failed to construct OCI Signer for REST: %s", e)
                span.record_exception(e)
                return {"error": f"Failed to construct signer: {e}"}

        session = _get_http_session()

        def post(path: str, payload: Dict) -> requests.Response:
            url = base_url + path
            return session.post(url, json=payload, auth=signer, timeout=60)

        created: Dict[str, Dict] = {}
        req_ids: List[str] = []
        try:
            # 1) VCN
            vcn_payload: Dict[str, object] = {
                "compartmentId": comp,
                "cidrBlock": cidr_block,
                "displayName": display_name,
            }
            if dns_label:
                vcn_payload["dnsLabel"] = dns_label
            resp = post("/vcns", vcn_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            vcn = resp.json()
            vcn_id = vcn["id"]
            created["vcn"] = {
                "id": vcn_id,
                "display_name": vcn.get("displayName"),
                "cidr_block": vcn.get("cidrBlock"),
                "dns_label": vcn.get("dnsLabel"),
            }

            # 2) Internet Gateway
            igw_payload = {
                "compartmentId": comp,
                "vcnId": vcn_id,
                "displayName": f"{display_name}-igw",
                "isEnabled": True,
            }
            resp = post("/internetGateways", igw_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            igw = resp.json()
            igw_id = igw["id"]
            created["internet_gateway"] = {"id": igw_id, "display_name": igw.get("displayName")}

            # 3) NAT Gateway
            nat_payload = {
                "compartmentId": comp,
                "vcnId": vcn_id,
                "displayName": f"{display_name}-nat",
            }
            resp = post("/natGateways", nat_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            nat = resp.json()
            nat_id = nat["id"]
            created["nat_gateway"] = {"id": nat_id, "display_name": nat.get("displayName")}

            # 4) Route Tables
            prt_payload = {
                "compartmentId": comp,
                "vcnId": vcn_id,
                "displayName": f"{display_name}-public-rt",
                "routeRules": [
                    {
                        "destination": "0.0.0.0/0",
                        "destinationType": "CIDR_BLOCK",
                        "networkEntityId": igw_id,
                        "description": "All traffic to Internet via IGW",
                    }
                ],
            }
            resp = post("/routeTables", prt_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            public_rt = resp.json()
            public_rt_id = public_rt["id"]
            created.setdefault("route_tables", {})["public"] = {
                "id": public_rt_id,
                "display_name": public_rt.get("displayName"),
            }

            privrt_payload = {
                "compartmentId": comp,
                "vcnId": vcn_id,
                "displayName": f"{display_name}-private-rt",
                "routeRules": [
                    {
                        "destination": "0.0.0.0/0",
                        "destinationType": "CIDR_BLOCK",
                        "networkEntityId": nat_id,
                        "description": "All egress via NAT",
                    }
                ],
            }
            resp = post("/routeTables", privrt_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            private_rt = resp.json()
            private_rt_id = private_rt["id"]
            created.setdefault("route_tables", {})["private"] = {
                "id": private_rt_id,
                "display_name": private_rt.get("displayName"),
            }

            # 5) Public Subnet
            pub_subnet_payload: Dict[str, object] = {
                "compartmentId": comp,
                "vcnId": vcn_id,
                "displayName": f"{display_name}-public-subnet",
                "cidrBlock": public_subnet_cidr,
                "prohibitPublicIpOnVnic": prohibit_public_ip_on_public_subnet,
                "routeTableId": public_rt_id,
            }
            if public_subnet_dns_label:
                pub_subnet_payload["dnsLabel"] = public_subnet_dns_label
            resp = post("/subnets", pub_subnet_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            pub_subnet = resp.json()
            created.setdefault("subnets", {})["public"] = {
                "id": pub_subnet["id"],
                "display_name": pub_subnet.get("displayName"),
                "cidr_block": pub_subnet.get("cidrBlock"),
                "dns_label": pub_subnet.get("dnsLabel"),
                "prohibit_public_ip_on_vnic": pub_subnet.get("prohibitPublicIpOnVnic"),
            }

            # 6) Private Subnet
            priv_subnet_payload = {
                "compartmentId": comp,
                "vcnId": vcn_id,
                "displayName": f"{display_name}-private-subnet",
                "cidrBlock": private_subnet_cidr,
                "prohibitPublicIpOnVnic": prohibit_public_ip_on_private_subnet,
                "routeTableId": private_rt_id,
            }
            if private_subnet_dns_label:
                priv_subnet_payload["dnsLabel"] = private_subnet_dns_label
            resp = post("/subnets", priv_subnet_payload)
            if "opc-request-id" in resp.headers:
                req_ids.append(resp.headers["opc-request-id"])
            resp.raise_for_status()
            priv_subnet = resp.json()
            created.setdefault("subnets", {})["private"] = {
                "id": priv_subnet["id"],
                "display_name": priv_subnet.get("displayName"),
                "cidr_block": priv_subnet.get("cidrBlock"),
                "dns_label": priv_subnet.get("dnsLabel"),
                "prohibit_public_ip_on_vnic": priv_subnet.get("prohibitPublicIpOnVnic"),
            }

            if req_ids:
                span.set_attribute("oci.request_id", req_ids[-1])

            return {
                "region": used_region,
                "compartment_id": comp,
                **created,
                "request_ids": req_ids,
                "api": "rest",
            }
        except requests.HTTPError as e:
            try:
                err_body = e.response.json()
            except Exception:
                err_body = e.response.text if getattr(e, "response", None) is not None else str(e)
            logging.error("REST error creating VCN with subnets: %s", err_body)
            span.record_exception(e)
            return {"error": str(err_body), "region": used_region, "compartment_id": comp, "api": "rest"}
        except Exception as e:
            logging.error("Error creating VCN with subnets (REST): %s", e)
            span.record_exception(e)
            return {"error": str(e), "region": used_region, "compartment_id": comp, "api": "rest"}

# =============================================================================
# Server Manifest Resource
# =============================================================================

def server_manifest() -> str:
    """
    Server manifest resource for capability discovery.
    Returns server metadata, available skills, and tool categorization.
    """
    manifest = {
        "name": "OCI MCP Network Server",
        "version": "1.0.0",
        "description": "OCI Network Infrastructure MCP Server for VCN, subnet, and gateway management",
        "capabilities": {
            "skills": [
                "network-topology",
                "vcn-management",
                "subnet-management",
                "security-assessment"
            ],
            "tools": {
                "tier1_instant": [
                    "healthcheck",
                    "doctor"
                ],
                "tier2_api": [
                    "list_vcns",
                    "list_subnets",
                    "summarize_public_endpoints"
                ],
                "tier3_heavy": [],
                "tier4_admin": [
                    "create_vcn",
                    "create_subnet",
                    "create_vcn_with_subnets",
                    "create_vcn_with_subnets_rest"
                ]
            }
        },
        "usage_guide": """
Start with Tier 1 tools for instant responses (< 100ms):
1. Use healthcheck() for basic server status
2. Use doctor() to verify configuration

Then use Tier 2 tools for API-based queries (1-10s):
1. Use list_vcns() to discover networks
2. Use list_subnets() to explore VCN topology
3. Use summarize_public_endpoints() for security assessment

Tier 4 admin tools require ALLOW_MUTATIONS=true:
- create_vcn_with_subnets() - Full VCN with gateways and subnets
""",
        "environment_variables": [
            "OCI_PROFILE",
            "OCI_REGION",
            "COMPARTMENT_OCID",
            "ALLOW_MUTATIONS",
            "MCP_OCI_PRIVACY"
        ]
    }
    return json.dumps(manifest, indent=2)

tools = [
    Tool.from_function(
        fn=lambda: {"status": "ok", "server": "oci-mcp-network", "pid": os.getpid()},
        name="healthcheck",
        description="Lightweight readiness/liveness check for the network server"
    ),
    Tool.from_function(
        fn=lambda: (lambda _cfg=get_oci_config(): {
            "server": "oci-mcp-network",
            "ok": True,
            "privacy": bool(__import__('mcp_oci_common.privacy', fromlist=['privacy_enabled']).privacy_enabled()),
            "region": _cfg.get("region"),
            "profile": os.getenv("OCI_PROFILE") or "DEFAULT",
            "tools": [t.name for t in tools]
        })(),
        name="doctor",
        description="Return server health, config summary, and masking status"
    ),
    Tool.from_function(
        fn=list_vcns,
        name="list_vcns",
        description="List VCNs in a compartment"
    ),
    Tool.from_function(
        fn=create_vcn,
        name="create_vcn",
        description="Create a new VCN (Virtual Cloud Network)"
    ),
    Tool.from_function(
        fn=list_subnets,
        name="list_subnets",
        description="List subnets in a VCN"
    ),
    Tool.from_function(
        fn=create_subnet,
        name="create_subnet",
        description="Create a new subnet in a VCN"
    ),
    Tool.from_function(
        fn=summarize_public_endpoints,
        name="summarize_public_endpoints",
        description="Summarize public endpoints in a compartment"
    ),
    Tool.from_function(
        fn=create_vcn_with_subnets,
        name="create_vcn_with_subnets",
        description="Create a VCN with public and private subnets, gateways, and route tables in one operation"
    ),
    Tool.from_function(
        fn=create_vcn_with_subnets_rest,
        name="create_vcn_with_subnets_rest",
        description="Create a VCN (plus IGW, NAT, route tables, public/private subnets) using OCI REST API with signed HTTP requests"
    ),
]

def get_tools():
    return [{"name": t.name, "description": t.description} for t in tools]

if __name__ == "__main__":
    # Lazy imports so importing this module (for UX tool discovery) doesn't require optional deps
    try:
        from prometheus_client import start_http_server as _start_http_server
    except Exception:
        _start_http_server = None
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor
    except Exception:
        _FastAPIInstrumentor = None

    # Expose Prometheus /metrics regardless of DEBUG (configurable via METRICS_PORT)
    if _start_http_server:
        try:
            _start_http_server(int(os.getenv("METRICS_PORT", "8006")))
        except Exception:
            pass
    # Validate MCP tool names at startup
    if not validate_and_log_tools(tools, "oci-mcp-network"):
        logging.error("MCP tool validation failed. Server will not start.")
        exit(1)

    # Apply privacy masking to all tools (wrapper)
    try:
        from mcp_oci_common.privacy import privacy_enabled as _pe, redact_payload as _rp
        from fastmcp.tools import Tool as _Tool
        _wrapped = []
        for _t in tools:
            _f = getattr(_t, "func", None) or getattr(_t, "handler", None)
            if not _f:
                _wrapped.append(_t)
                continue
            def _mk(f):
                def _w(*a, **k):
                    out = f(*a, **k)
                    return _rp(out) if _pe() else out
                _w.__name__ = getattr(f, "__name__", "tool")
                _w.__doc__ = getattr(f, "__doc__", "")
                return _w
            _wrapped.append(_Tool.from_function(_mk(_f), name=_t.name, description=_t.description))
        tools = _wrapped
    except Exception:
        pass

    mcp = FastMCP(tools=tools, name="oci-mcp-network")

    # Register the server manifest resource
    @mcp.resource("server://manifest")
    def get_manifest() -> str:
        return server_manifest()
    if _FastAPIInstrumentor:
        try:
            if hasattr(mcp, "app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "app"))
            elif hasattr(mcp, "fastapi_app"):
                _FastAPIInstrumentor.instrument_app(getattr(mcp, "fastapi_app"))
            else:
                _FastAPIInstrumentor().instrument()
        except Exception:
            try:
                _FastAPIInstrumentor().instrument()
            except Exception:
                pass

    # Optional Pyroscope profiling (non-breaking)
    try:
        ENABLE_PYROSCOPE = os.getenv("ENABLE_PYROSCOPE", "false").lower() in ("1", "true", "yes", "on")
        if ENABLE_PYROSCOPE:
            import pyroscope
            pyroscope.configure(
                application_name=os.getenv("PYROSCOPE_APP_NAME", "oci-mcp-network"),
                server_address=os.getenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040"),
                sample_rate=int(os.getenv("PYROSCOPE_SAMPLE_RATE", "100")),
                detect_subprocesses=True,
                enable_logging=True,
            )
    except Exception:
        # Never break server if profiler not available
        pass

    mcp.run()
