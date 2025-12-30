---
name: oci-database
version: 2.0.0
description: OCI Database Management capabilities
parent: oci-mcp-unified
domain: database
---

# Database Domain

## Purpose
Comprehensive management of Oracle Cloud Infrastructure database services including Autonomous Database (ADB), DB Systems, and MySQL.

## Available Tools

### Autonomous Database
| Tool | Tier | Description |
|------|------|-------------|
| `oci_database_list_autonomous` | 2 | List ADBs in compartment |
| `oci_database_get_autonomous` | 2 | Get ADB details |
| `oci_database_start_autonomous` | 4 | Start stopped ADB |
| `oci_database_stop_autonomous` | 4 | Stop running ADB |

### DB Systems
| Tool | Tier | Description |
|------|------|-------------|
| `oci_database_list_dbsystems` | 2 | List DB Systems |

### Metrics & Backups
| Tool | Tier | Description |
|------|------|-------------|
| `oci_database_get_metrics` | 3 | Get database performance metrics |
| `oci_database_list_backups` | 2 | List database backups |

## Usage Examples

### List Autonomous Databases
```python
result = await oci_database_list_autonomous({
    "compartment_id": "ocid1.compartment.oc1...",
    "workload_type": "OLTP",
    "lifecycle_state": "AVAILABLE"
})
```

### Get Database Details
```python
result = await oci_database_get_autonomous({
    "database_id": "ocid1.autonomousdatabase.oc1...",
    "response_format": "json"
})
```

### Start/Stop Database
```python
# Requires ALLOW_MUTATIONS=true
result = await oci_database_start_autonomous({
    "database_id": "ocid1.autonomousdatabase.oc1...",
    "wait_for_state": true
})
```

## Workload Types
- **OLTP** - Autonomous Transaction Processing
- **DW** - Autonomous Data Warehouse  
- **AJD** - Autonomous JSON Database
- **APEX** - Autonomous Application Express

## Safety Controls
- Write operations require `ALLOW_MUTATIONS=true`
- State validation before start/stop
- Idempotent operations (start already running = success)
