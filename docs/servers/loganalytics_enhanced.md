# Enhanced OCI Log Analytics Server

Exposes advanced `oci:loganalytics:*` tools for Oracle Cloud Infrastructure Logging Analytics with security analysis capabilities.

## Overview

The Enhanced Log Analytics server provides comprehensive security analysis, MITRE ATT&CK integration, and advanced analytics capabilities based on the logan-server implementation. It includes both the original Log Analytics tools and new enhanced security analysis features.

## Enhanced Tools

### Core Security Analysis Tools

#### `oci:loganalytics:execute_logan_query`
Execute a Log Analytics query with enhanced security analysis capabilities.

**Parameters:**
- `query` (string, required): OCI Log Analytics query string
- `compartment_id` (string, optional): OCI compartment ID (uses root compartment if not specified)
- `query_name` (string, optional): Optional name for the query
- `time_range` (string, optional): Time range (1h, 6h, 12h, 24h, 1d, 7d, 30d, 1w, 1m) - Default: 24h
- `max_count` (integer, optional): Maximum number of results - Default: 1000

**Example:**
```json
{
  "query": "'Event Name' = 'UserLoginFailed' and Time > dateRelative(24h) | stats count by 'User Name'",
  "compartment_id": "ocid1.compartment.oc1..example",
  "time_range": "24h",
  "max_count": 100
}
```

#### `oci:loganalytics:search_security_events`
Search for security events using natural language or predefined patterns.

**Parameters:**
- `search_term` (string, required): Natural language description or specific security event pattern
- `compartment_id` (string, optional): OCI compartment ID
- `event_type` (string, optional): Event type filter (login, privilege_escalation, network_anomaly, data_exfiltration, malware, all) - Default: all
- `time_range` (string, optional): Time range for the search - Default: 24h
- `limit` (integer, optional): Maximum number of results - Default: 100

**Example:**
```json
{
  "search_term": "failed login attempts in the last 24 hours",
  "compartment_id": "ocid1.compartment.oc1..example",
  "event_type": "login",
  "time_range": "24h"
}
```

#### `oci:loganalytics:get_mitre_techniques`
Search for MITRE ATT&CK techniques in the logs.

**Parameters:**
- `compartment_id` (string, required): OCI compartment ID
- `technique_id` (string, optional): Specific MITRE technique ID (e.g., T1003, T1110) or "all" - Default: all
- `category` (string, optional): MITRE tactic category - Default: all
- `time_range` (string, optional): Time range for the analysis - Default: 30d

**Example:**
```json
{
  "compartment_id": "ocid1.compartment.oc1..example",
  "technique_id": "T1110",
  "time_range": "7d"
}
```

#### `oci:loganalytics:analyze_ip_activity`
Analyze activity for specific IP addresses.

**Parameters:**
- `ip_address` (string, required): IP address to analyze
- `compartment_id` (string, optional): OCI compartment ID
- `analysis_type` (string, optional): Type of analysis (full, authentication, network, threat_intel, communication_patterns) - Default: full
- `time_range` (string, optional): Time range for the analysis - Default: 24h

**Example:**
```json
{
  "ip_address": "192.168.1.100",
  "compartment_id": "ocid1.compartment.oc1..example",
  "analysis_type": "full",
  "time_range": "24h"
}
```

### Advanced Analytics Tools

#### `oci:loganalytics:perform_statistical_analysis`
Execute statistical analysis using stats, timestats, and eventstats commands.

**Parameters:**
- `base_query` (string, required): Base query to analyze statistically
- `compartment_id` (string, required): OCI compartment ID
- `statistics_type` (string, optional): Type of statistical analysis (stats, timestats, eventstats, top, bottom, frequent, rare) - Default: stats
- `aggregations` (array, optional): Statistical functions to apply
- `group_by` (array, optional): Fields to group by
- `time_interval` (string, optional): Time interval for timestats (e.g., "5m", "1h", "1d")
- `time_range` (string, optional): Time range for analysis - Default: 24h

**Example:**
```json
{
  "base_query": "'Event Name' = 'UserLogin'",
  "compartment_id": "ocid1.compartment.oc1..example",
  "statistics_type": "timestats",
  "time_interval": "1h",
  "time_range": "24h"
}
```

#### `oci:loganalytics:perform_advanced_analytics`
Execute advanced analytics queries using OCI Log Analytics specialized commands.

**Parameters:**
- `base_query` (string, required): Base query to analyze (without analytics command)
- `compartment_id` (string, required): OCI compartment ID
- `analytics_type` (string, optional): Type of advanced analytics (cluster, link, nlp, classify, outlier, sequence, geostats, timecluster) - Default: cluster
- `parameters` (object, optional): Parameters specific to the analytics type
- `time_range` (string, optional): Time range for analysis - Default: 24h

**Example:**
```json
{
  "base_query": "'Event Name' = 'UserLogin'",
  "compartment_id": "ocid1.compartment.oc1..example",
  "analytics_type": "cluster",
  "parameters": {
    "max_clusters": 5,
    "group_by": ["User", "Source IP"]
  }
}
```

### Utility Tools

#### `oci:loganalytics:validate_query`
Validate an OCI Logging Analytics query syntax.

**Parameters:**
- `query` (string, required): Query to validate
- `fix` (boolean, optional): Attempt to automatically fix common syntax errors - Default: false

**Example:**
```json
{
  "query": "'Event Name' = 'UserLogin' and Time > dateRelative(24h)",
  "fix": true
}
```

#### `oci:loganalytics:get_documentation`
Get documentation and help for OCI Logging Analytics and Logan queries.

**Parameters:**
- `topic` (string, optional): Documentation topic (query_syntax, field_names, functions, time_filters, operators, mitre_mapping, examples, troubleshooting) - Default: query_syntax
- `search_term` (string, optional): Specific term to search for in documentation

**Example:**
```json
{
  "topic": "mitre_mapping",
  "search_term": "T1110"
}
```

#### `oci:loganalytics:check_connection`
Check OCI Logging Analytics connection and authentication.

**Parameters:**
- `compartment_id` (string, required): OCI compartment ID
- `test_query` (boolean, optional): Run a test query to verify connectivity - Default: true

**Example:**
```json
{
  "compartment_id": "ocid1.compartment.oc1..example",
  "test_query": true
}
```

## Security Query Patterns

The enhanced server includes predefined security query patterns for common security analysis scenarios:

### Authentication Events
- **Failed Logins**: Detects failed authentication attempts
- **Successful Logins**: Tracks successful authentication events

### Privilege Escalation
- **Sudo Usage**: Monitors sudo command usage
- **Role Assumption**: Tracks role assumption events

### Network Security
- **Suspicious Network Activity**: Detects blocked connections and suspicious traffic
- **Port Scanning**: Identifies port scanning attempts

### Data Security
- **Data Exfiltration**: Detects potential data theft attempts
- **Malware Detection**: Identifies malware-related activities

## MITRE ATT&CK Integration

The server includes mapping for common MITRE ATT&CK techniques:

- **T1003**: OS Credential Dumping
- **T1005**: Data from Local System
- **T1041**: Exfiltration Over C2 Channel
- **T1043**: Commonly Used Port
- **T1046**: Network Service Scanning
- **T1055**: Process Injection
- **T1059**: Command and Scripting Interpreter
- **T1078**: Valid Accounts
- **T1110**: Brute Force
- **T1548**: Abuse Elevation Control Mechanism

## Query Syntax Guide

### Field Names
Always quote field names with spaces:
```
'Event Name' = 'UserLogin'
'User Name' contains 'admin'
'IP Address' = '192.168.1.100'
```

### Time Filters
Use capitalized 'Time' field:
```
Time > dateRelative(24h)  # Last 24 hours
Time > dateRelative(7d)   # Last 7 days
```

### Common Patterns
```sql
-- Failed logins
'Event Name' = 'UserLoginFailed' and Time > dateRelative(24h) | stats count by 'User Name'

-- Network connections
'Log Source' = 'VCN Flow Logs' and Time > dateRelative(1h) | stats count by 'Source IP'

-- MITRE techniques
'Technique_id' is not null and Time > dateRelative(7d) | stats count by 'Technique_id'
```

## Usage Examples

### Basic Security Analysis
```
Search for failed login attempts in the last 24 hours
```

### MITRE Technique Analysis
```
Find all credential access techniques in the last 30 days
```

### IP Investigation
```
Analyze all activity for IP address 192.168.1.100 in the last 24 hours
```

### Advanced Analytics
```
Perform clustering analysis on user login events
```

## Configuration

### Environment Variables
- `OCI_COMPARTMENT_ID`: Default compartment ID
- `OCI_REGION`: OCI region
- `OCI_NAMESPACE`: Object storage namespace (auto-detected)
- `OCI_USER_ID`: User OCID (from config file)
- `OCI_TENANCY_ID`: Tenancy OCID (from config file)
- `OCI_FINGERPRINT`: Key fingerprint (from config file)
- `OCI_KEY_FILE`: Private key file path (from config file)

### OCI Configuration
The server uses the standard OCI configuration file (`~/.oci/config`) or environment variables for authentication.

## Troubleshooting

### Common Issues

**"Missing input" Error**
- Check field name capitalization: use 'Time' not 'time'
- Quote field names with spaces
- Verify operator syntax

**Authentication Errors**
- Verify OCI CLI configuration: `oci iam user get --user-id <user-ocid>`
- Check compartment permissions
- Validate key file permissions

**No Results**
- Verify time range is appropriate
- Check compartment has log data
- Ensure log sources are configured

### Performance Tips

1. Always include time filters
2. Use specific field filters early in queries
3. Limit result sets with `| head 100`
4. Use indexed fields for filtering

## Integration with FastMCP

The enhanced Log Analytics tools are integrated into the FastMCP server and can be accessed through the `loganalytics` service:

```bash
python -m mcp_oci_fastmcp loganalytics
```

This provides access to all enhanced Log Analytics capabilities through the FastMCP framework.
