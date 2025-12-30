---
name: oci-security
version: 2.0.0
description: OCI Security, IAM, and Cloud Guard capabilities
parent: oci-mcp-unified
domain: security
---

# Security Domain

## Purpose
Comprehensive identity and access management, Cloud Guard problem detection,
and security posture assessment for Oracle Cloud Infrastructure.

## Available Tools

### IAM Management
| Tool | Tier | Description |
|------|------|-------------|
| `oci_security_list_users` | 2 | List IAM users with filtering |
| `oci_security_get_user` | 2 | Get user details with groups and API keys |
| `oci_security_list_groups` | 2 | List IAM groups |
| `oci_security_list_policies` | 2 | List IAM policies with statements |

### Cloud Guard
| Tool | Tier | Description |
|------|------|-------------|
| `oci_security_list_cloud_guard_problems` | 2 | List security problems by risk level |

### Security Analysis
| Tool | Tier | Description |
|------|------|-------------|
| `oci_security_audit` | 3 | Comprehensive security audit |

## Common Patterns

### Security Posture Assessment
```python
# 1. Run comprehensive security audit
audit = oci_security_audit({
    "include_iam": True,
    "include_cloud_guard": True,
    "include_network_security": True
})

# 2. Check for critical Cloud Guard problems
problems = oci_security_list_cloud_guard_problems({
    "risk_level": "CRITICAL",
    "lifecycle_state": "ACTIVE"
})

# 3. Review policies with broad permissions
policies = oci_security_list_policies({
    "name_contains": "admin"
})
```

### User Investigation
```python
# 1. Find user by name
users = oci_security_list_users({
    "name_contains": "john",
    "lifecycle_state": "ACTIVE"
})

# 2. Get detailed user info with group memberships
user_details = oci_security_get_user({
    "user_id": "ocid1.user.oc1..xxx",
    "include_groups": True,
    "include_api_keys": True
})
```

## Response Examples

### Markdown Format
```markdown
# Security Audit Report

**Audit Time:** 2024-01-15T10:30:00Z
**Compartment:** Tenancy Root

## Security Score
**Overall Score:** 72/100 - 🟡 Fair

## IAM Summary
- **Users:** 45 (Active: 38)
- **Groups:** 12
- **Policies:** 28

**Findings:**
- ⚠️ Review MFA status for 38 active users
- ⚠️ 3 policies with 'manage all-resources' detected

## Cloud Guard Summary
- **Critical Problems:** 2
- **High Problems:** 5
- **Total Active Problems:** 15

## Recommendations
1. Address 2 critical Cloud Guard problems immediately
```

### JSON Format
```json
{
  "audit_time": "2024-01-15T10:30:00Z",
  "compartment_name": "Tenancy Root",
  "security_score": {
    "overall": 72
  },
  "iam_summary": {
    "total_users": 45,
    "active_users": 38,
    "total_groups": 12,
    "total_policies": 28,
    "findings": ["Review MFA status for 38 active users"]
  },
  "cloud_guard_summary": {
    "total": 15,
    "critical": 2,
    "high": 5,
    "medium": 8
  },
  "recommendations": [
    "Address 2 critical Cloud Guard problems immediately"
  ]
}
```

## Risk Levels

Cloud Guard problems are classified by risk:
- 🔴 **CRITICAL** - Immediate action required
- 🟠 **HIGH** - Address within 24 hours
- 🟡 **MEDIUM** - Address within 1 week
- 🟢 **LOW** - Address during maintenance
- ⚪ **MINOR** - Informational
