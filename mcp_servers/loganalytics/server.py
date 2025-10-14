"""Enhanced MCP Server: OCI Log Analytics with Security Analysis and REST API
Based on logan-server implementation with advanced security features and direct REST API calls for queries.

Tools are exposed as `oci:loganalytics:<action>`.
Includes security analysis, MITRE ATT&CK integration, and advanced analytics.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mcp_oci_common import get_oci_config
from mcp_oci_common.response import with_meta
from mcp_oci_common.observability import init_tracing, init_metrics, tool_span
from opentelemetry import trace

import oci  # type: ignore
import requests
from oci.signer import Signer

# Set up tracing with proper Resource so service.name is set (avoids unknown_service)
os.environ.setdefault("OTEL_SERVICE_NAME", "oci-mcp-loganalytics")
init_tracing(service_name="oci-mcp-loganalytics")
init_metrics()
tracer = trace.get_tracer("oci-mcp-loganalytics")


@dataclass
class SecurityQuery:
    """Security query definition"""
    name: str
    description: str
    queries: List[str]
    mitre_techniques: List[str] = None
    severity: str = "medium"


class SecurityQueryMapper:
    """Maps security analysis types to OCI Log Analytics queries"""
    
    def __init__(self):
        self.security_queries = {
            "failed_logins": SecurityQuery(
                name="Failed Login Attempts",
                description="Detect failed authentication attempts",
                queries=[
                    "* | where contains('Log Entry', 'Failed password') or contains('Log Entry', 'authentication failure')",
                    "* | where 'Event Name' = 'AuthenticationFailure'",
                    "* | where contains('Message', 'login failed') or contains('Message', 'authentication failed')",
                    "* | search 'failed' 'login' OR 'authentication' 'failure'"
                ],
                mitre_techniques=["T1110", "T1078"],
                severity="high"
            ),
            "privilege_escalation": SecurityQuery(
                name="Privilege Escalation",
                description="Detect privilege escalation attempts",
                queries=[
                    "* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'su:')",
                    "* | where contains('Event Name', 'Assume') or contains('Event Name', 'Escalate')",
                    "* | search 'sudo' OR 'privilege' 'escalation' OR 'assume' 'role'"
                ],
                mitre_techniques=["T1548", "T1078"],
                severity="high"
            ),
            "suspicious_network": SecurityQuery(
                name="Suspicious Network Activity",
                description="Detect suspicious network connections",
                queries=[
                    "* | where contains('Log Entry', 'connection refused') or contains('Log Entry', 'blocked')",
                    "* | search 'blocked' 'connection' OR 'suspicious' 'traffic' OR 'firewall' 'deny'",
                    "* | where 'Action' = 'BLOCK' or 'Action' = 'DENY' or 'Action' = 'REJECT'"
                ],
                mitre_techniques=["T1046", "T1043"],
                severity="medium"
            ),
            "data_exfiltration": SecurityQuery(
                name="Data Exfiltration",
                description="Detect potential data exfiltration attempts",
                queries=[
                    "* | where contains('Log Entry', 'large download') or contains('Log Entry', 'bulk transfer')",
                    "* | search 'exfiltration' OR 'data' 'theft' OR 'unauthorized' 'download'",
                    "* | where 'Event Name' = 'DataAccess' and 'Action' = 'READ'"
                ],
                mitre_techniques=["T1041", "T1005"],
                severity="high"
            ),
            "malware": SecurityQuery(
                name="Malware Detection",
                description="Detect malware-related activities",
                queries=[
                    "* | where contains('Log Entry', 'malware') or contains('Log Entry', 'virus')",
                    "* | search 'malware' OR 'virus' OR 'trojan' OR 'ransomware'",
                    "* | where 'Event Name' = 'MalwareDetected' or 'Event Name' = 'ThreatDetected'"
                ],
                mitre_techniques=["T1055", "T1059"],
                severity="critical"
            )
        }
        
        self.mitre_techniques = {
            "T1003": "OS Credential Dumping",
            "T1005": "Data from Local System",
            "T1041": "Exfiltration Over C2 Channel",
            "T1043": "Commonly Used Port",
            "T1046": "Network Service Scanning",
            "T1055": "Process Injection",
            "T1059": "Command and Scripting Interpreter",
            "T1078": "Valid Accounts",
            "T1110": "Brute Force",
            "T1548": "Abuse Elevation Control Mechanism"
        }

    def get_security_query(self, query_type: str, time_period_minutes: int = 60) -> Dict[str, Any]:
        """Get security query for a specific type"""
        if query_type not in self.security_queries:
            return {
                "success": False,
                "error": f"Unknown security query type: {query_type}",
                "available_types": list(self.security_queries.keys())
            }
        
        query_def = self.security_queries[query_type]
        
        # Add time filter to queries (append in a syntax-safe way)
        time_filter = f"Time > dateRelative({time_period_minutes}m)"
        enhanced_queries = []
        
        for query in query_def.queries:
            q = query
            # If query already constrains Time, keep as-is
            if "Time >" in q or "time >" in q:
                enhanced_queries.append(q)
                continue
            # If query already has a where clause, extend it
            if "| where" in q:
                enhanced_queries.append(f"{q} and {time_filter}")
            else:
                # For search/other pipelines, add a where stage
                enhanced_queries.append(f"{q} | where {time_filter}")
        
        return {
            "success": True,
            "query_type": query_type,
            "description": query_def.description,
            "queries": enhanced_queries,
            "mitre_techniques": query_def.mitre_techniques,
            "severity": query_def.severity,
            "time_period_minutes": time_period_minutes
        }

    def get_mitre_technique_query(self, technique_id: str, time_period_minutes: int = 60) -> Dict[str, Any]:
        """Get query for specific MITRE technique"""
        if technique_id not in self.mitre_techniques:
            return {
                "success": False,
                "error": f"Unknown MITRE technique: {technique_id}",
                "available_techniques": list(self.mitre_techniques.keys())
            }
        
        technique_name = self.mitre_techniques[technique_id]
        time_filter = f"Time > dateRelative({time_period_minutes}m)"
        
        # Map technique to query patterns
        technique_queries = {
            "T1003": [f"* | where contains('Log Entry', 'credential') or contains('Log Entry', 'password') and {time_filter}"],
            "T1005": [f"* | where contains('Log Entry', 'file access') or contains('Log Entry', 'data access') and {time_filter}"],
            "T1041": [f"* | where contains('Log Entry', 'network') or contains('Log Entry', 'connection') and {time_filter}"],
            "T1043": [f"* | where contains('Log Entry', 'port') or contains('Log Entry', 'service') and {time_filter}"],
            "T1046": [f"* | where contains('Log Entry', 'scan') or contains('Log Entry', 'probe') and {time_filter}"],
            "T1055": [f"* | where contains('Log Entry', 'injection') or contains('Log Entry', 'process') and {time_filter}"],
            "T1059": [f"* | where contains('Log Entry', 'command') or contains('Log Entry', 'script') and {time_filter}"],
            "T1078": [f"* | where contains('Log Entry', 'login') or contains('Log Entry', 'authentication') and {time_filter}"],
            "T1110": [f"* | where contains('Log Entry', 'failed') or contains('Log Entry', 'brute') and {time_filter}"],
            "T1548": [f"* | where contains('Log Entry', 'sudo') or contains('Log Entry', 'elevate') and {time_filter}"]
        }
        
        queries = technique_queries.get(technique_id, [f"* | where contains('Log Entry', '{technique_name.lower()}') and {time_filter}"])
        
        return {
            "success": True,
            "technique_id": technique_id,
            "technique_name": technique_name,
            "queries": queries,
            "time_period_minutes": time_period_minutes
        }


def _format_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Convert time range string to start/end datetimes"""
    now = datetime.now(timezone.utc)
    
    time_mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "24h": timedelta(hours=24),
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "1w": timedelta(weeks=1),
        "1m": timedelta(days=30)
    }
    
    delta = time_mapping.get(time_range, timedelta(hours=24))
    start_time = now - delta
    
    return start_time, now


def _minutes_from_time_range(time_range: str) -> int:
    """Convert strings like '60m', '24h', '7d', '1w', '30d' to minutes."""
    if not isinstance(time_range, str):
        return 60
    tr = time_range.strip().lower()
    try:
        if tr.endswith("m"):
            return int(tr[:-1])
        if tr.endswith("h"):
            return int(tr[:-1]) * 60
        if tr.endswith("d"):
            return int(tr[:-1]) * 1440
        if tr.endswith("w"):
            return int(tr[:-1]) * 7 * 1440
        # plain number → minutes
        return int(tr)
    except Exception:
        return 60


def run_query_legacy(
    namespace_name: str,
    query_string: str,
    time_start: str,
    time_end: str,
    subsystem: str | None = None,
    max_total_count: int | None = None,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Legacy-compatible query tool: run a query for a namespace and explicit time window.

    Uses direct REST call with SDK Signer, matching the QueryDetails schema.
    """
    if requests is None or Signer is None or oci is None:
        return with_meta({"error": "Required libraries not available"}, success=False)

    try:
        cfg = get_oci_config(profile_name=profile)
        if region:
            cfg["region"] = region

        signer = Signer(
            tenancy=cfg["tenancy"],
            user=cfg["user"],
            fingerprint=cfg["fingerprint"],
            private_key_file_location=cfg["key_file"],
            pass_phrase=cfg.get("pass_phrase"),
        )

        # Determine region strictly: prefer explicit cfg, then env; no silent fallback
        api_region = cfg.get("region") or os.getenv("OCI_REGION")
        if not api_region:
            return with_meta({"error": "OCI region not set for Log Analytics. Set OCI_REGION or pass region param."}, success=False)
        url = f"https://loganalytics.{api_region}.oci.oraclecloud.com/20200601/namespaces/{namespace_name}/search/actions/query"

        body = {
            "queryString": query_string,
            "subSystem": subsystem or "LOG",
            "maxTotalCount": max_total_count or 1000,
            "timeFilter": {"timeStart": time_start, "timeEnd": time_end},
            "shouldIncludeTotalCount": True,
        }
        params = {"limit": max_total_count or 1000}

        resp = requests.post(url, json=body, auth=signer, params=params, timeout=60)
        if not resp.ok:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        results = data.get("results") or data.get("items") or []
        return with_meta(
            {
                "namespace": namespace_name,
                "query": query_string,
                "results": results,
                "count": len(results),
                "time_start": time_start,
                "time_end": time_end,
            },
            success=True,
            message=f"Query executed successfully. Found {len(results)} results.",
        )
    except Exception as e:
        return with_meta({"error": str(e)}, success=False, message=f"Legacy query failed: {e}")


def _get_namespace(compartment_id: str, profile: str | None = None, region: str | None = None) -> str:
    """Get Log Analytics namespace for the tenancy.

    Tries official SDK list_namespaces; falls back to object storage namespace; last resort returns tenancy or provided compartment_id.
    """
    # Load config using supported signature and apply region override
    cfg = get_oci_config(profile_name=profile)
    if region:
        cfg["region"] = region

    tenancy_id = cfg.get("tenancy") or compartment_id

    # Prefer proper Log Analytics namespace discovery (requires tenancy OCID)
    try:
        la = oci.log_analytics.LogAnalyticsClient(cfg)
        resp = la.list_namespaces(compartment_id=tenancy_id)
        items = getattr(resp.data, 'items', None) or []
        if items:
            return items[0].namespace_name
    except Exception:
        pass

    # Fallback to Object Storage namespace if available
    try:
        os_client = oci.object_storage.ObjectStorageClient(cfg)
        return os_client.get_namespace().data
    except Exception:
        # Last resort: return tenancy or the provided compartment_id
        return tenancy_id


def execute_query(
    query: str,
    compartment_id: Optional[str] = None,
    query_name: str | None = None,
    time_range: str = "24h",
    max_count: int = 1000,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute a Log Analytics query using direct REST API with query enhancement"""
    with tool_span(tracer, "execute_query", mcp_server="oci-mcp-loganalytics") as span:
        config = get_oci_config(profile_name=profile)
        compartment_id = compartment_id or config["tenancy"]
        if requests is None or Signer is None:
            return with_meta({"error": "Required libraries not available"}, success=False)

        try:
            # Enhance the query before execution
            from .query_enhancer import enhance_log_analytics_query
            enhancement_result = enhance_log_analytics_query(query)

            # Use enhanced query if available and valid
            enhanced_query = enhancement_result.get('enhanced_query', query)
            validation_issues = {
                'errors': enhancement_result.get('errors', []),
                'warnings': enhancement_result.get('warnings', []),
                'suggestions': enhancement_result.get('suggestions', [])
            }

            # If there are critical errors, return them
            if not enhancement_result.get('is_valid', True) and enhancement_result.get('errors'):
                return with_meta({
                    "error": "Query validation failed",
                    "validation_errors": validation_issues['errors'],
                    "suggestions": validation_issues['suggestions'],
                    "original_query": query,
                    "enhanced_query": enhanced_query
                }, success=False, message=f"Query validation failed: {'; '.join(validation_issues['errors'])}")

            # Use the enhanced query for execution
            query_to_execute = enhanced_query
            # Load config and apply region override
            config = get_oci_config(profile_name=profile)
            if region:
                config["region"] = region
            namespace = _get_namespace(compartment_id, profile, region)

            # Convert time range
            start_time, end_time = _format_time_range(time_range)

            # Create signer
            signer = Signer(
                tenancy=config["tenancy"],
                user=config["user"],
                fingerprint=config["fingerprint"],
                private_key_file_location=config["key_file"],
                pass_phrase=config.get("pass_phrase")
            )

            # Build URL
            api_region = region or config.get("region") or os.getenv("OCI_REGION")
            if not api_region:
                return with_meta({"error": "OCI region not set for Log Analytics. Set OCI_REGION or pass region param."}, success=False)
            url = f"https://loganalytics.{api_region}.oci.oraclecloud.com/20200601/namespaces/{namespace}/search/actions/query"

            # Build query details
            query_details = {
                "subSystem": "LOG",
                "queryString": query_to_execute,
                "shouldRunAsync": False,
                "shouldIncludeTotalCount": True,
                "compartmentId": compartment_id,
                "compartmentIdInSubtree": True,
                "timeFilter": {
                    "timeStart": start_time.isoformat().replace('+00:00', 'Z'),
                    "timeEnd": end_time.isoformat().replace('+00:00', 'Z'),
                    "timeZone": os.getenv("TIME_ZONE", "UTC")
                },
                "maxTotalCount": max_count
            }

            params = {"limit": max_count}

            response = requests.post(url, json=query_details, auth=signer, params=params, timeout=60)

            # Synchronous completion
            if response.status_code == 200:
                data = response.json()
                results = data.get("results") or data.get("items") or []
                total_count = data.get("totalCount") or data.get("total_count")
            # Accepted → server may have started an async work request. Try to poll.
            elif response.status_code == 201:
                data = response.json() if response.content else {}
                # Try to obtain work request id from headers or payload
                wr_id = (
                    response.headers.get("opc-work-request-id")
                    or data.get("workRequestId")
                    or data.get("work_request_id")
                )
                results = []
                total_count = None
                if wr_id:
                    try:
                        # Use SDK to poll get_query_result for completion
                        la_client = oci.log_analytics.LogAnalyticsClient(config)
                        poll_resp = la_client.get_query_result(
                            namespace_name=namespace,
                            work_request_id=wr_id,
                            should_include_columns=True,
                            should_include_fields=True,
                        )
                        pdata = getattr(poll_resp, "data", None)
                        if pdata and getattr(pdata, "rows", None):
                            # Normalize to list of row dicts with columns
                            cols = []
                            if getattr(pdata, "columns", None):
                                for i, c in enumerate(pdata.columns):
                                    cols.append(
                                        getattr(c, "column_name", None)
                                        or getattr(c, "name", None)
                                        or getattr(c, "display_name", None)
                                        or f"col_{i}"
                                    )
                            results = []
                            for r in (getattr(pdata, "rows", None) or []):
                                vals = getattr(r, "values", None) or getattr(r, "data", None) or []
                                results.append(dict(zip(cols, vals)) if cols and len(vals) == len(cols) else {"values": vals})
                            total_count = len(results)
                    except Exception:
                        # If polling fails, fall back to empty results with info below
                        pass
            else:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")

            return with_meta(
                {
                    "query": query,
                    "enhanced_query": query_to_execute if query_to_execute != query else None,
                    "query_name": query_name,
                    "time_range": time_range,
                    "namespace": namespace,
                    "compartment_id": compartment_id,
                    "results": results,
                    "count": int(total_count) if isinstance(total_count, (int, float)) else len(results),
                    "validation": validation_issues if validation_issues['warnings'] or validation_issues['suggestions'] else None
                },
                success=True,
                message=f"Query executed successfully. Found {len(results)} results." + (" (Query was enhanced)" if query_to_execute != query else "")
            )
        except Exception as e:
            return with_meta(
                {"error": str(e)},
                success=False,
                message=f"Query execution failed: {str(e)}"
            )

# The rest of the functions remain the same as in enhanced, since they call execute_query

# ... (copy the rest of the enhanced code here, from search_security_events to the end)

def search_security_events(
    search_term: str,
    compartment_id: str,
    event_type: str = "all",
    time_range: str = "24h",
    limit: int = 100,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    with tool_span(tracer, "search_security_events", mcp_server="oci-mcp-loganalytics") as span:
        try:
            mapper = SecurityQueryMapper()

            # Normalize event_type and map synonyms; then infer from search_term if needed
            synonyms = {
                "login": "failed_logins",
                "failed_login": "failed_logins",
                "failed_logins": "failed_logins",
                "network_anomaly": "suspicious_network",
                "network": "suspicious_network",
                "privilege_escalation": "privilege_escalation",
                "data_exfiltration": "data_exfiltration",
                "malware": "malware",
                "all": "all",
            }
            if event_type and event_type in synonyms and event_type != "all":
                event_type = synonyms[event_type]

            if event_type == "all":
                search_lower = (search_term or "").lower()
                if any(term in search_lower for term in ["login", "auth", "signin", "failed"]):
                    event_type = "failed_logins"
                elif any(term in search_lower for term in ["privilege", "escalation", "sudo"]):
                    event_type = "privilege_escalation"
                elif any(term in search_lower for term in ["network", "connection", "traffic", "blocked", "deny"]):
                    event_type = "suspicious_network"
                elif any(term in search_lower for term in ["data", "exfiltration", "theft", "download"]):
                    event_type = "data_exfiltration"
                elif any(term in search_lower for term in ["malware", "virus", "trojan", "ransom"]):
                    event_type = "malware"
                else:
                    event_type = "failed_logins"  # Default fallback

            # Get security query using parsed time window
            minutes = _minutes_from_time_range(time_range)
            query_result = mapper.get_security_query(event_type, minutes)

            if not query_result.get("success"):
                return with_meta(
                    {"error": query_result.get("error")},
                    success=False,
                    message=f"Security query mapping failed: {query_result.get('error')}"
                )

            # Execute the first query
            query = query_result["queries"][0]
            result = execute_query(
                query=query,
                compartment_id=compartment_id,
                query_name=f"security_search_{event_type}",
                time_range=time_range,
                max_count=limit,
                profile=profile,
                region=region
            )

            # Parse the result
            result_data = json.loads(result)

            return with_meta(
                {
                    "search_term": search_term,
                    "event_type": event_type,
                    "query_used": query,
                    "mitre_techniques": query_result.get("mitre_techniques", []),
                    "severity": query_result.get("severity", "medium"),
                    "results": result_data.get("results", []),
                    "count": result_data.get("count", 0)
                },
                success=result_data.get("success", False),
                message=f"Security event search completed. Found {result_data.get('count', 0)} events."
            )
        except Exception as e:
            return with_meta(
                {"error": str(e)},
                success=False,
                message=f"Security event search failed: {str(e)}"
            )

def get_mitre_techniques(
    compartment_id: str,
    technique_id: str = "all",
    category: str = "all",
    time_range: str = "30d",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Search for MITRE ATT&CK techniques in the logs"""
    try:
        mapper = SecurityQueryMapper()
        
        if technique_id == "all":
            # Return all available techniques
            return with_meta(
                {
                    "techniques": mapper.mitre_techniques,
                    "count": len(mapper.mitre_techniques)
                },
                success=True,
                message=f"Found {len(mapper.mitre_techniques)} MITRE techniques"
            )
        
        # Get specific technique query using parsed time window
        minutes = _minutes_from_time_range(time_range)
        query_result = mapper.get_mitre_technique_query(technique_id, minutes)
        
        if not query_result.get("success"):
            return with_meta(
                {"error": query_result.get("error")},
                success=False,
                message=f"MITRE technique query failed: {query_result.get('error')}"
            )
        
        # Execute the query
        query = query_result["queries"][0]
        result = execute_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"mitre_technique_{technique_id}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "technique_id": technique_id,
                "technique_name": query_result.get("technique_name"),
                "query_used": query,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"MITRE technique analysis completed. Found {result_data.get('count', 0)} events for technique {technique_id}."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"MITRE technique analysis failed: {str(e)}"
        )


def analyze_ip_activity(
    ip_address: str,
    compartment_id: str,
    analysis_type: str = "full",
    time_range: str = "24h",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Analyze activity for specific IP addresses"""
    try:
        # Build query based on analysis type
        time_filter = f"Time > dateRelative({time_range})"
        
        if analysis_type == "authentication":
            query = f"* | where contains('Source IP', '{ip_address}') and (contains('Log Entry', 'login') or contains('Log Entry', 'auth')) and {time_filter} | stats count by 'Event Name', 'User'"
        elif analysis_type == "network":
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') and {time_filter} | stats count by 'Source IP', 'Destination IP', 'Port'"
        elif analysis_type == "threat_intel":
            query = f"* | where contains('Source IP', '{ip_address}') and (contains('Log Entry', 'threat') or contains('Log Entry', 'malware') or contains('Log Entry', 'suspicious')) and {time_filter}"
        elif analysis_type == "communication_patterns":
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') and {time_filter} | stats count by 'Protocol', 'Port' | sort -count"
        else:  # full
            query = f"* | where contains('Source IP', '{ip_address}') or contains('Destination IP', '{ip_address}') and {time_filter} | stats count by 'Event Name', 'Log Source' | sort -count"
        
        # Execute the query
        result = execute_query(
            query=query,
            compartment_id=compartment_id,
            query_name=f"ip_analysis_{analysis_type}_{ip_address}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "ip_address": ip_address,
                "analysis_type": analysis_type,
                "query_used": query,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"IP activity analysis completed. Found {result_data.get('count', 0)} events for IP {ip_address}."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"IP activity analysis failed: {str(e)}"
        )


def perform_statistical_analysis(
    base_query: str,
    compartment_id: str,
    statistics_type: str = "stats",
    aggregations: List[Dict] = None,
    group_by: List[str] = None,
    time_interval: str = None,
    time_range: str = "24h",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute statistical analysis using stats, timestats, and eventstats commands"""
    try:
        # Build statistical query
        if statistics_type == "timestats" and time_interval:
            stats_query = f"{base_query} | timestats {time_interval} count by {', '.join(group_by) if group_by else '1'}"
        elif statistics_type == "eventstats":
            stats_query = f"{base_query} | eventstats count by {', '.join(group_by) if group_by else '1'}"
        elif statistics_type == "top":
            stats_query = f"{base_query} | top 10 by count"
        elif statistics_type == "bottom":
            stats_query = f"{base_query} | bottom 10 by count"
        elif statistics_type == "frequent":
            stats_query = f"{base_query} | frequent 10"
        elif statistics_type == "rare":
            stats_query = f"{base_query} | rare 10"
        else:  # stats
            # Build aggregations using LA-compliant syntax:
            # - COUNT() (no arg) is accepted; or COUNT(<fieldName>)
            # - Other functions keep their field argument if provided
            def _agg_fmt(agg: Dict) -> str:
                fn = str(agg.get("function", "count")).upper()
                field = agg.get("field")
                alias = agg.get("alias", fn.lower())
                if fn == "COUNT":
                    expr = "COUNT()" if not field else f"COUNT({field})"
                else:
                    expr = f"{fn}({field})" if field else f"{fn}()"
                return f"{expr} as {alias}"
            effective_aggs = aggregations or [{"function": "count"}]
            agg_str = ", ".join(_agg_fmt(a) for a in effective_aggs)
            group_str = f" by {', '.join(group_by)}" if group_by else ""
            stats_query = f"{base_query} | stats {agg_str}{group_str}"
        
        # Execute the query
        result = execute_query(
            query=stats_query,
            compartment_id=compartment_id,
            query_name=f"statistical_analysis_{statistics_type}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "base_query": base_query,
                "statistics_type": statistics_type,
                "statistical_query": stats_query,
                "aggregations": aggregations,
                "group_by": group_by,
                "time_interval": time_interval,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"Statistical analysis completed. Found {result_data.get('count', 0)} results."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Statistical analysis failed: {str(e)}"
        )


def perform_advanced_analytics(
    base_query: str,
    compartment_id: str,
    analytics_type: str = "cluster",
    parameters: Dict = None,
    time_range: str = "24h",
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Execute advanced analytics queries using OCI Log Analytics specialized commands"""
    try:
        # Build analytics query
        params = parameters or {}
        
        if analytics_type == "cluster":
            group_by = params.get("group_by", ["1"])
            max_clusters = params.get("max_clusters", 5)
            analytics_query = f"{base_query} | cluster by {', '.join(group_by)} max_clusters={max_clusters}"
        elif analytics_type == "outlier":
            threshold = params.get("threshold", 0.7)
            analytics_query = f"{base_query} | outlier threshold={threshold}"
        elif analytics_type == "nlp":
            analytics_query = f"{base_query} | nlp"
        elif analytics_type == "classify":
            analytics_query = f"{base_query} | classify"
        elif analytics_type == "sequence":
            pattern = params.get("sequence_pattern", "")
            analytics_query = f"{base_query} | sequence {pattern}"
        elif analytics_type == "geostats":
            lat_field = params.get("geoFields", {}).get("latitude", "latitude")
            lon_field = params.get("geoFields", {}).get("longitude", "longitude")
            analytics_query = f"{base_query} | geostats {lat_field}, {lon_field}"
        elif analytics_type == "timecluster":
            analytics_query = f"{base_query} | timecluster"
        else:  # link
            analytics_query = f"{base_query} | link"
        
        # Execute the query
        result = execute_query(
            query=analytics_query,
            compartment_id=compartment_id,
            query_name=f"advanced_analytics_{analytics_type}",
            time_range=time_range,
            profile=profile,
            region=region
        )
        
        # Parse the result
        result_data = json.loads(result)
        
        return with_meta(
            {
                "base_query": base_query,
                "analytics_type": analytics_type,
                "analytics_query": analytics_query,
                "parameters": parameters,
                "results": result_data.get("results", []),
                "count": result_data.get("count", 0)
            },
            success=result_data.get("success", False),
            message=f"Advanced analytics completed. Found {result_data.get('count', 0)} results."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Advanced analytics failed: {str(e)}"
        )


def validate_query(
    query: str,
    fix: bool = False,
) -> str:
    """Validate an OCI Logging Analytics query syntax"""
    try:
        # Basic validation rules
        validation_errors = []
        suggestions = []
        
        # Check for common issues
        if "!=" in query and "null" in query:
            if fix:
                query = query.replace("!= null", '!= ""').replace("is not null", '!= ""')
                suggestions.append("Fixed null comparison operators for OCI API compatibility")
            else:
                validation_errors.append("Use '!= \"\"' instead of '!= null' for OCI API compatibility")
        
        if "Time >" not in query and "time >" not in query:
            suggestions.append("Consider adding a time filter like 'Time > dateRelative(24h)' for better performance")
        
        if not query.strip():
            validation_errors.append("Query cannot be empty")
        
        # Check for proper field quoting
        import re
        unquoted_fields = re.findall(r'\b[A-Z][a-zA-Z\s]+\b', query)
        if unquoted_fields:
            suggestions.append(f"Consider quoting field names with spaces: {unquoted_fields}")
        
        is_valid = len(validation_errors) == 0
        
        return with_meta(
            {
                "query": query,
                "is_valid": is_valid,
                "validation_errors": validation_errors,
                "suggestions": suggestions,
                "fixed_query": query if fix else None
            },
            success=is_valid,
            message=f"Query validation {'passed' if is_valid else 'failed'} with {len(validation_errors)} errors and {len(suggestions)} suggestions."
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Query validation failed: {str(e)}"
        )


def validate_query(query: str) -> dict:
    """Validate and enhance a Log Analytics query for syntax and field mapping issues

    Args:
        query: The Log Analytics query to validate and enhance

    Returns:
        Dict containing validation results, suggestions, and enhanced query
    """
    try:
        from .query_enhancer import enhance_log_analytics_query

        result = enhance_log_analytics_query(query)

        return {
            "success": True,
            "validation_result": {
                "original_query": result['original_query'],
                "enhanced_query": result['enhanced_query'],
                "is_valid": result['is_valid'],
                "errors": result['errors'],
                "warnings": result['warnings'],
                "suggestions": result['suggestions'],
                "timestamp": result['timestamp']
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Query validation failed: {str(e)}",
            "validation_result": {
                "original_query": query,
                "enhanced_query": query,
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "suggestions": ["Please check query syntax"],
                "timestamp": datetime.utcnow().isoformat()
            }
        }


def get_documentation(
    topic: str = "query_syntax",
    search_term: str | None = None,
) -> str:
    """Get documentation and help for OCI Logging Analytics and Logan queries"""
    try:
        documentation = {
            "query_syntax": {
                "title": "OCI Log Analytics Query Syntax",
                "content": {
                    "field_names": "Always quote field names with spaces: 'Event Name' = 'UserLogin'",
                    "time_filters": "Use 'Time > dateRelative(24h)' for time-based filtering",
                    "operators": "Supported operators: =, !=, >, <, >=, <=, contains, in, not in",
                    "functions": "Common functions: stats, timestats, eventstats, top, bottom, frequent, rare",
                    "examples": [
                        "Failed logins: 'Event Name' = 'UserLoginFailed' and Time > dateRelative(24h) | stats count by 'User Name'",
                        "Network connections: 'Log Source' = 'VCN Flow Logs' and Time > dateRelative(1h) | stats count by 'Source IP'",
                        "MITRE techniques: 'Technique_id' is not null and Time > dateRelative(7d) | stats count by 'Technique_id'"
                    ]
                }
            },
            "mitre_mapping": {
                "title": "MITRE ATT&CK Technique Mapping",
                "content": {
                    "T1003": "OS Credential Dumping",
                    "T1005": "Data from Local System", 
                    "T1041": "Exfiltration Over C2 Channel",
                    "T1043": "Commonly Used Port",
                    "T1046": "Network Service Scanning",
                    "T1055": "Process Injection",
                    "T1059": "Command and Scripting Interpreter",
                    "T1078": "Valid Accounts",
                    "T1110": "Brute Force",
                    "T1548": "Abuse Elevation Control Mechanism"
                }
            },
            "troubleshooting": {
                "title": "Troubleshooting Guide",
                "content": {
                    "common_issues": [
                        "Missing input: Check field name capitalization and quoting",
                        "Authentication errors: Verify OCI configuration and permissions",
                        "No results: Check time range and compartment access",
                        "Syntax errors: Use validate_query tool for automatic fixes"
                    ],
                    "performance_tips": [
                        "Always include time filters for better performance",
                        "Use specific field filters early in queries",
                        "Limit result sets with '| head 100'",
                        "Use indexed fields for filtering"
                    ]
                }
            },
            "examples": {
                "title": "Practical Logan queries",
                "content": {
                    "sources_last_24h": "* | where Time > dateRelative(24h) | stats COUNT as logrecords by 'Log Source' | sort -logrecords | head 100",
                    "top_failed_logins_24h": "* | where Time > dateRelative(24h) and 'Event Name' = 'UserLoginFailed' | stats COUNT as failures by 'User Name' | sort -failures | head 20"
                }
            }
        }
        
        if topic not in documentation:
            available_topics = list(documentation.keys())
            return with_meta(
                {"error": f"Unknown topic: {topic}", "available_topics": available_topics},
                success=False,
                message=f"Unknown documentation topic. Available topics: {', '.join(available_topics)}"
            )
        
        doc_content = documentation[topic]
        
        # Filter by search term if provided
        if search_term:
            filtered_content = {}
            search_lower = search_term.lower()
            for key, value in doc_content["content"].items():
                if isinstance(value, str) and search_lower in value.lower():
                    filtered_content[key] = value
                elif isinstance(value, list):
                    filtered_list = [item for item in value if search_lower in str(item).lower()]
                    if filtered_list:
                        filtered_content[key] = filtered_list
            doc_content["content"] = filtered_content
        
        return with_meta(
            {
                "topic": topic,
                "search_term": search_term,
                "documentation": doc_content
            },
            success=True,
            message=f"Documentation retrieved for topic: {topic}"
        )
    except Exception as e:
        return with_meta(
            {"error": str(e)},
            success=False,
            message=f"Documentation retrieval failed: {str(e)}"
        )


def check_oci_connection(
    compartment_id: str,
    test_query: bool = True,
    profile: str | None = None,
    region: str | None = None,
) -> str:
    """Check OCI Logging Analytics connection and authentication"""
    try:
        namespace = _get_namespace(compartment_id, profile, region)
        
        connection_info = {
            "compartment_id": compartment_id,
            "namespace": namespace,
            "region": region or "default",
            "profile": profile or "default",
            "connection_status": "success"
        }
        
        if test_query:
            # Run a simple test query
            test_result = execute_query(
                query="* | head 1",
                compartment_id=compartment_id,
                query_name="connection_test",
                time_range="1h",
                max_count=1,
                profile=profile,
                region=region
            )
            
            test_data = json.loads(test_result)
            count = int(test_data.get("count", 0)) if isinstance(test_data.get("count", 0), (int, float, str)) else 0
            has_logs = count > 0
            connection_info["records_found"] = count
            connection_info["has_logs"] = has_logs
            # Treat success as having connectivity; include has_logs to drive UX messaging
            connection_info["test_query_success"] = bool(test_data.get("_meta", {}).get("success", False))
            connection_info["test_query_message"] = test_data.get("message", "")
        
        return with_meta(
            connection_info,
            success=True,
            message="OCI Log Analytics connection successful"
        )
    except Exception as e:
        return with_meta(
            {
                "compartment_id": compartment_id,
                "connection_status": "failed",
                "error": str(e)
            },
            success=False,
            message=f"OCI Log Analytics connection failed: {str(e)}"
        )


def exadata_cost_drilldown_logan(
    analysis_type: str = "basic_cost_monitoring",
    compartment_id: str = "",
    time_range: str = "30d",
    query_name: str = "",
    profile: str | None = None,
    region: str | None = None,
) -> dict:
    """Exadata cost drilldown using Logan queries (alternative to Usage API)

    Args:
        analysis_type: Type of analysis (basic_cost_monitoring, optimization, anomaly_detection, regional_analysis)
        compartment_id: OCI compartment ID
        time_range: Time range for analysis
        query_name: Specific Logan query to run (optional)
        profile: OCI profile name
        region: OCI region

    Returns:
        Dict containing Logan query results and analysis
    """
    try:
        from .exadata_logan_queries import get_query_recommendations, ExadataLoganQueries

        with tool_span(tracer, "exadata_cost_drilldown_logan", mcp_server="oci-mcp-loganalytics") as span:
            span.set_attribute("analysis_type", analysis_type)
            span.set_attribute("compartment_id", compartment_id)
            span.set_attribute("time_range", time_range)

            catalog = ExadataLoganQueries()

            if query_name:
                # Run specific query
                logan_query = catalog.get_query(query_name)
                if not logan_query:
                    return {
                        "success": False,
                        "error": f"Query '{query_name}' not found",
                        "available_queries": list(catalog.get_all_queries().keys())
                    }

                query_result = execute_query(
                    query=logan_query.query,
                    time_range=time_range,
                    compartment_id=compartment_id,
                    profile=profile,
                    region=region
                )

                if query_result.get("success"):
                    return {
                        "success": True,
                        "analysis_type": "specific_logan_query",
                        "query_name": logan_query.name,
                        "query_description": logan_query.description,
                        "use_case": logan_query.use_case,
                        "results": query_result.get("results", []),
                        "result_count": len(query_result.get("results", [])),
                        "query_used": logan_query.query
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Logan query execution failed: {query_result.get('error', 'Unknown error')}",
                        "query_name": logan_query.name
                    }

            else:
                # Run recommended queries for analysis type
                recommendations = get_query_recommendations(analysis_type)
                if not recommendations:
                    return {
                        "success": False,
                        "error": f"No queries found for analysis type: {analysis_type}",
                        "available_types": ["basic_cost_monitoring", "optimization", "anomaly_detection", "regional_analysis"]
                    }

                results = {}
                total_records = 0

                for rec in recommendations:
                    query_result = execute_query(
                        query=rec["query"],
                        time_range=time_range,
                        compartment_id=compartment_id,
                        profile=profile,
                        region=region
                    )

                    if query_result.get("success"):
                        query_results = query_result.get("results", [])
                        results[rec["name"]] = {
                            "description": rec["description"],
                            "use_case": rec["use_case"],
                            "results": query_results,
                            "record_count": len(query_results),
                            "query": rec["query"]
                        }
                        total_records += len(query_results)
                    else:
                        results[rec["name"]] = {
                            "description": rec["description"],
                            "error": query_result.get("error", "Query failed"),
                            "record_count": 0
                        }

                span.set_attribute("queries_executed", len(recommendations))
                span.set_attribute("total_records", total_records)

                return {
                    "success": True,
                    "analysis_type": analysis_type,
                    "logan_queries_executed": len(recommendations),
                    "total_records": total_records,
                    "time_range": time_range,
                    "compartment_id": compartment_id,
                    "query_results": results,
                    "note": "Using Logan (Log Analytics) queries instead of Usage API for Exadata cost analysis"
                }

    except Exception as e:
        error_msg = f"Logan Exadata cost drilldown failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "analysis_type": analysis_type,
            "timestamp": datetime.utcnow().isoformat()
        }


def analyze_exadata_costs(
    query: str,
    time_range: str = "30d",
    compartment_id: str = "",
    max_count: int = 2000,
    profile: str | None = None,
    region: str | None = None,
) -> dict:
    """Comprehensive Exadata cost analysis with optimization recommendations

    Args:
        query: Base Exadata cost query to analyze
        time_range: Time range for analysis (default: 30d)
        compartment_id: OCI compartment ID
        max_count: Maximum number of results to analyze
        profile: OCI profile name
        region: OCI region

    Returns:
        Dict containing comprehensive analysis report with optimizations, insights, and visualizations
    """
    try:
        from .exadata_optimizer import analyze_exadata_costs as run_exadata_analysis
        import time

        with tool_span(tracer, "analyze_exadata_costs", mcp_server="oci-mcp-loganalytics") as span:
            span.set_attribute("query", query)
            span.set_attribute("time_range", time_range)
            span.set_attribute("compartment_id", compartment_id)

            # Execute the original query to get baseline results
            start_time = time.time()
            base_results = execute_query(
                query=query,
                time_range=time_range,
                compartment_id=compartment_id,
                max_count=max_count,
                profile=profile,
                region=region
            )
            query_time = time.time() - start_time

            if not base_results.get("success", False):
                return {
                    "success": False,
                    "error": f"Base query execution failed: {base_results.get('error', 'Unknown error')}",
                    "analysis_type": "exadata_cost_optimization"
                }

            # Extract results for analysis
            query_results = base_results.get("results", [])

            # Generate comprehensive analysis
            analysis_report = run_exadata_analysis(
                query=query,
                results=query_results,
                query_time=query_time,
                time_range=time_range
            )

            # Add execution metadata
            analysis_report.update({
                "success": True,
                "base_query_results": {
                    "record_count": len(query_results),
                    "execution_time": round(query_time, 2),
                    "time_range": time_range,
                    "compartment_id": compartment_id
                }
            })

            span.set_attribute("analysis_generated", True)
            span.set_attribute("records_analyzed", len(query_results))

            return analysis_report

    except Exception as e:
        error_msg = f"Exadata cost analysis failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "analysis_type": "exadata_cost_optimization",
            "timestamp": datetime.utcnow().isoformat()
        }


def register_tools() -> list[dict[str, Any]]:
    return [
        # Core Query Tools
        {
            "name": "oci_loganalytics_execute_query",
            "description": "Execute a Log Analytics query with enhanced security analysis capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "OCI Log Analytics query string"},
                    "query_name": {"type": "string", "description": "Optional name for the query"},
                    "time_range": {"type": "string", "description": "Time range (1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m)", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "max_count": {"type": "integer", "description": "Maximum number of results", "default": 1000},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["query"],
            },
            "handler": execute_query,
        },
        {
            "name": "oci_loganalytics_search_security_events",
            "description": "Search for security events using natural language or predefined patterns",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "Natural language description or specific security event pattern"},
                    "event_type": {"type": "string", "enum": ["login", "privilege_escalation", "network_anomaly", "data_exfiltration", "malware", "all"], "default": "all"},
                    "time_range": {"type": "string", "description": "Time range for the search", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 100},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["search_term", "compartment_id"],
            },
            "handler": search_security_events,
        },
        {
            "name": "oci_loganalytics_get_mitre_techniques",
            "description": "Search for MITRE ATT&CK techniques in the logs",
            "parameters": {
                "type": "object",
                "properties": {
                    "technique_id": {"type": "string", "description": "Specific MITRE technique ID (e.g., T1003, T1110) or 'all'"},
                    "category": {"type": "string", "enum": ["initial_access", "execution", "persistence", "privilege_escalation", "defense_evasion", "credential_access", "discovery", "lateral_movement", "collection", "command_and_control", "exfiltration", "impact", "all"], "default": "all"},
                    "time_range": {"type": "string", "description": "Time range for the analysis", "default": "30d"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": get_mitre_techniques,
        },
        {
            "name": "oci_loganalytics_analyze_ip_activity",
            "description": "Analyze activity for specific IP addresses",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip_address": {"type": "string", "description": "IP address to analyze"},
                    "analysis_type": {"type": "string", "enum": ["full", "authentication", "network", "threat_intel", "communication_patterns"], "default": "full"},
                    "time_range": {"type": "string", "description": "Time range for the analysis", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["ip_address", "compartment_id"],
            },
            "handler": analyze_ip_activity,
        },
        # Advanced Analytics Tools
        {
            "name": "oci_loganalytics_perform_statistical_analysis",
            "description": "Execute statistical analysis using stats, timestats, and eventstats commands",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_query": {"type": "string", "description": "Base query to analyze statistically"},
                    "statistics_type": {"type": "string", "enum": ["stats", "timestats", "eventstats", "top", "bottom", "frequent", "rare"], "default": "stats"},
                    "aggregations": {"type": "array", "description": "Statistical functions to apply"},
                    "group_by": {"type": "array", "description": "Fields to group by"},
                    "time_interval": {"type": "string", "description": "Time interval for timestats (e.g., '5m', '1h', '1d')"},
                    "time_range": {"type": "string", "description": "Time range for analysis", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["base_query", "compartment_id"],
            },
            "handler": perform_statistical_analysis,
        },
        {
            "name": "oci_loganalytics_perform_advanced_analytics",
            "description": "Execute advanced analytics queries using OCI Log Analytics specialized commands",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_query": {"type": "string", "description": "Base query to analyze (without analytics command)"},
                    "analytics_type": {"type": "string", "enum": ["cluster", "link", "nlp", "classify", "outlier", "sequence", "geostats", "timecluster"], "default": "cluster"},
                    "parameters": {"type": "object", "description": "Parameters specific to the analytics type"},
                    "time_range": {"type": "string", "description": "Time range for analysis", "default": "24h"},
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["base_query", "compartment_id"],
            },
            "handler": perform_advanced_analytics,
        },
        # Utility Tools
        {
            "name": "oci_loganalytics_validate_query",
            "description": "Validate an OCI Logging Analytics query syntax",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query to validate"},
                    "fix": {"type": "boolean", "description": "Attempt to automatically fix common syntax errors", "default": False},
                },
                "required": ["query"],
            },
            "handler": validate_query,
        },
        {
            "name": "oci_loganalytics_get_documentation",
            "description": "Get documentation and help for OCI Logging Analytics and Logan queries",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "enum": ["query_syntax", "field_names", "functions", "time_filters", "operators", "mitre_mapping", "examples", "troubleshooting"], "default": "query_syntax"},
                    "search_term": {"type": "string", "description": "Specific term to search for in documentation"},
                },
            },
            "handler": get_documentation,
        },
        {
            "name": "oci_loganalytics_check_oci_connection",
            "description": "Check OCI Logging Analytics connection and authentication",
            "parameters": {
                "type": "object",
                "properties": {
                    "compartment_id": {"type": "string", "description": "OCI compartment ID"},
                    "test_query": {"type": "boolean", "description": "Run a test query to verify connectivity", "default": True},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["compartment_id"],
            },
            "handler": check_oci_connection,
        },
        # Original tools for backward compatibility
        {
            "name": "oci_loganalytics_run_query",
            "description": "Run a Log Analytics query for a namespace and time range (legacy)",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace_name": {"type": "string"},
                    "query_string": {"type": "string"},
                    "time_start": {"type": "string", "description": "ISO8601"},
                    "time_end": {"type": "string", "description": "ISO8601"},
                    "subsystem": {"type": "string", "description": "Optional subsystem filter"},
                    "max_total_count": {"type": "integer", "description": "Optional cap on rows"},
                    "profile": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["namespace_name", "query_string", "time_start", "time_end"],
            },
            "handler": run_query_legacy,
        },
        {
            "name": "oci_loganalytics_validate_query",
            "description": "Validate and enhance a Log Analytics query for syntax and field mapping issues",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The Log Analytics query to validate and enhance"
                    }
                },
                "required": ["query"],
            },
            "handler": validate_query,
        },
        {
            "name": "oci_loganalytics_exadata_cost_drilldown",
            "description": "Exadata cost drilldown using Logan queries (alternative to Usage API service_cost_drilldown)",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["basic_cost_monitoring", "optimization", "anomaly_detection", "regional_analysis", "cost_drilldown"],
                        "description": "Type of analysis to perform",
                        "default": "basic_cost_monitoring"
                    },
                    "compartment_id": {
                        "type": "string",
                        "description": "OCI compartment ID"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range for analysis (1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m)",
                        "default": "30d"
                    },
                    "query_name": {
                        "type": "string",
                        "description": "Specific Logan query to run (optional): basic_exadata_costs, high_cost_databases, daily_cost_trends, etc."
                    },
                    "profile": {
                        "type": "string",
                        "description": "OCI profile name"
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region"
                    }
                },
                "required": ["compartment_id"],
            },
            "handler": exadata_cost_drilldown_logan,
        },
        {
            "name": "oci_loganalytics_analyze_exadata_costs",
            "description": "Comprehensive Exadata cost analysis with optimization recommendations, performance insights, and visualization data",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Base Exadata cost query to analyze (e.g., your working query)"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range for analysis (1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m)",
                        "default": "30d"
                    },
                    "compartment_id": {
                        "type": "string",
                        "description": "OCI compartment ID"
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of results to analyze",
                        "default": 2000
                    },
                    "profile": {
                        "type": "string",
                        "description": "OCI profile name"
                    },
                    "region": {
                        "type": "string",
                        "description": "OCI region"
                    }
                },
                "required": ["query", "compartment_id"],
            },
            "handler": analyze_exadata_costs,
        },
    ]
