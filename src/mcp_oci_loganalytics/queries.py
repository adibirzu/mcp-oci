from __future__ import annotations

from typing import Any

SNIPPETS: dict[str, str] = {
    # Count errors by source, descending, with optional limit
    "top_errors_by_source": "search \"error\" | stats count() by source | sort -count | limit {limit}",
    # Count messages by log group
    "count_by_log_group": "stats count() by logGroup | sort -count | limit {limit}",
}

# Additional Log Analytics working queries
SNIPPETS.update({
    # General stats by Log Source
    "stats_by_log_source": "* | stats count as logrecords by 'Log Source' | sort -logrecords",

    # All network traffic (example from VCN Flow logs)
    "all_network_traffic": "'Log Source' = 'OCI VCN Flow Unified Schema Logs' | eval vol = unit('Content Size Out', byte) | stats sum(vol) as Volume, trend(sum(vol)) | compare timeshift = auto",

    # Top 10 Denied Connections by Source
    "top10_denied_connections_by_source": "'Log Source' in ('OCI VCN Flow Unified Schema Logs') and Action in (drop, reject) | rename 'Source IP' as Source | stats count by Source | top 10 Count",

    # Top 10 Destination Ports by Traffic
    "top10_destination_ports_by_traffic": "'Log Source' = 'OCI VCN Flow Unified Schema Logs' | eval vol = unit('Content Size Out', byte) | stats sum(vol) as Volume by 'Destination Port' | top 10 Volume",

    # Top 10 Windows Failed Logins
    "top10_windows_failed_logins": "'Log Source' = 'Windows Security Events' and 'Security Result' = denied | fields 'Security Actor Endpoint Account', 'Security Category', 'Security Result', 'Security Command', 'Security Action', 'Security Actor Endpoint Name', 'Security Destination Endpoint Network Name', 'Security Destination Resource' | stats count by 'Security Destination Endpoint Account' | sort -Count | head 10",

    # Failed SSH Logins by Destination
    "failed_ssh_logins_by_destination": "'Security Original Name' in (sshd, ssh) and 'Security Category' = authentication.login and 'Security Result' = denied | fields 'Security Actor Endpoint Network Address' as Destination | timestats count as Count by Destination",

    # Suricata Dashboard queries
    "suricata_signature": "'Log Source' = com.oraclecloud.logging.custom.Suricatalogs | fields SuricataSignature, SuricataSignatureID | stats count as logrecords by SuricataSignature | sort -logrecords",
    "suricata_id": "'Log Source' = com.oraclecloud.logging.custom.Suricatalogs | fields SuricataSignature, SuricataSignatureID | stats count as logrecords by SuricataSignatureID | sort -logrecords",
    "suricata_signature_percentage": "'Log Source' = com.oraclecloud.logging.custom.Suricatalogs and 'Event Type' = alert | fields SuricataSignature, SuricataSignatureID, 'Event Type', -'Host Name (Server)', -Entity, -'Entity Type', -'Problem Priority', -Label, -'Log Source' | stats count as logrecords by SuricataSignature",
    "suricata_destination_ip_percentage": "'Log Source' = com.oraclecloud.logging.custom.Suricatalogs and 'Event Type' = alert | fields SuricataSignature, SuricataSignatureID, 'Event Type', -'Host Name (Server)', -Entity, -'Entity Type', -'Problem Priority', -Label, -'Log Source' | stats count as logrecords by 'Destination IP'",

    # WAF protection rules
    "waf_protection_rules": "'Log Source' = 'OCI WAF Logs' and 'Request Protection Rule IDs' != null | stats count('Host IP Address (Client)') by 'Request Protection Rule IDs', 'Host IP Address (Client)'",
    "waf_request_protection_capabilities_check_action": "'Log Source' = 'OCI WAF Logs' and 'Security Module' not like in ('%requestAccessControl%', '%responseAccessControl%', '%requestRateLimiting%', '%requestProtection%') and 'Security Module' != null and 'Request Protection Rule IDs Data' != null | rename 'Request Protection Rule IDs' as 'Request Protection Capabilities' | stats count by 'Request Protection Capabilities' | sort -Count | lookup table = 'Web Application Firewall Protection Capabilities' select Key as Key, Name, Description, Tags, _Version using 'Request Protection Capabilities' = 'Protection Capabilities' | fields Name, Key, Description, _Version | rename _Version as Version",

    # Windows Sysmon detected Events
    "windows_sysmon_detected_events": "'Log Source' = 'Windows Sysmon Events' and 'Event ID' != null | stats count by 'Event ID' | sort -Count | lookup table = MITRE select 'Event ID' as 'Event ID', 'Event Name', Channel, 'Audit Category', 'OSSEM Id' using 'Event ID' | fields 'Event ID', 'Event Name', Channel, 'Audit Category', 'OSSEM Id'",
    "windows_sysmon_not_technique_t1574_002": "'Log Source' = 'Windows Sysmon Events' and Technique_id != T1574.002 | fields Technique_id, 'Destination IP', 'Source IP' | timestats count as logrecords by 'Log Source'",
    "mitre_technique_id_non_system": "'Log Source' = 'Windows Sysmon Events' and User != 'NT AUTHORITY\\\\SYSTEM' | timestats count as logrecords by Technique_id",

    # VCN Flow anomaly patterns
    "port_scan_detection": "'Log Source' = 'OCI VCN Flow Unified Schema Logs' and 'Destination Port' != 0 | fields 'Destination IP' | timestats span = 5minute distinctcount('Destination Port') as Port_count by 'Source IP' | where Port_count > 100 | sort -Port_count",
    "dest_ip_fanout_detection": "'Log Source' = 'OCI VCN Flow Unified Schema Logs' and 'Destination Port' != 0 | timestats span = 5minute distinctcount('Destination IP') as DestIp_count by 'Source IP' | where DestIp_count > 50 | sort -DestIp_count",
})


def render_snippet(name: str, params: dict[str, Any]) -> str:
    if name not in SNIPPETS:
        raise ValueError(f"Unknown snippet: {name}")
    template = SNIPPETS[name]
    # Provide defaults for common placeholders
    params = {"limit": 50, **params}
    try:
        return template.format(**params)
    except KeyError as e:
        missing = e.args[0]
        raise ValueError(f"Missing parameter '{missing}' for snippet '{name}'")
