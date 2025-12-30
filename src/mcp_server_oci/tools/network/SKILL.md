---
name: oci-network
version: 2.0.0
description: OCI Network (VCN, Subnets, Security Lists) management capabilities
parent: oci-mcp-unified
domain: network
---

# Network Domain

## Purpose
Comprehensive management of OCI Virtual Cloud Networks (VCNs), Subnets, and Security Lists.

## Available Tools

### VCN Management
| Tool | Tier | Description |
|------|------|-------------|
| `oci_network_list_vcns` | 2 | List VCNs in a compartment |
| `oci_network_get_vcn` | 2 | Get VCN details with subnets and security lists |

### Subnet Management
| Tool | Tier | Description |
|------|------|-------------|
| `oci_network_list_subnets` | 2 | List subnets with CIDR and type info |

### Security Lists
| Tool | Tier | Description |
|------|------|-------------|
| `oci_network_list_security_lists` | 2 | List security lists with rules |
| `oci_network_analyze_security` | 2 | Analyze rules for security risks |

## Common Patterns

### List VCNs
```python
oci_network_list_vcns({
    "compartment_id": "ocid1.compartment...",
    "lifecycle_state": "AVAILABLE"
})
```

### Get VCN with Details
```python
oci_network_get_vcn({
    "vcn_id": "ocid1.vcn...",
    "include_subnets": True,
    "include_security_lists": True
})
```

### Analyze Security Rules
```python
oci_network_analyze_security({
    "vcn_id": "ocid1.vcn...",
    "response_format": "markdown"
})
```

## Security Analysis

The `oci_network_analyze_security` tool identifies:
- **Open to World (0.0.0.0/0)**: Rules allowing traffic from anywhere
- **Sensitive Ports Exposed**: SSH (22), RDP (3389), database ports (1521, 3306, 5432)
- **Risk Levels**: HIGH, MEDIUM, LOW with recommendations

## Response Examples

### Markdown Format
```markdown
# Virtual Cloud Networks

**Total:** 3 VCN(s)

| Name | CIDR Block | State | Subnets | Created |
|------|------------|-------|---------|---------|
| production-vcn | 10.0.0.0/16 | AVAILABLE | 6 | 2024-01-15 |
| development-vcn | 10.1.0.0/16 | AVAILABLE | 4 | 2024-02-20 |
```

### Security Analysis
```markdown
# Security Rule Analysis

**Total Rules Analyzed:** 45
**Risky Rules Found:** 3

## ⚠️ Risky Rules

### 🔴 default_security_list
**Risk Level:** HIGH
**Reason:** Rule exposes sensitive port 22 to the internet
**Recommendation:** Restrict access to port 22 to specific IP addresses
