# Compute Instance Optimization Summary

## Overview

The compute MCP server has been optimized to provide comprehensive instance information including volumes and costs, making it ideal for chat/Slack interactions where users need complete instance details in a single query.

## Key Enhancements

### 1. Enhanced Instance Listing with Volumes

The `list_instances` function now includes:
- **Instance Configuration**: Name, shape, OCPUs, memory, lifecycle state
- **IP Addresses**: Primary and all secondary IPs (both private and public)
- **Boot Volumes**: All boot volumes attached to each instance with size and configuration
- **Block Volumes**: All block volumes attached to each instance with size and configuration
- **Total Volume Size**: Quick reference for total storage per instance

### 2. Instance Cost Calculation

New `get_instance_cost` function provides:
- **Compute Costs**: Instance compute costs for specified time window
- **Storage Costs**: Costs for all attached boot volumes and block volumes
- **Per-Volume Breakdown**: Individual cost for each volume
- **Total Cost**: Combined compute and storage costs

### 3. Comprehensive Instance Details

New `get_comprehensive_instance_details` function returns:
- All instance configuration details
- IP addresses (optional)
- Volume information (optional)
- Cost information (optional)
- All in a single API call

## Usage Examples

### Query All Instances in a Compartment

```python
# Get all instances with volumes and IPs
instances = list_instances(
    compartment_id="[Link to Secure Variable: OCI_COMPARTMENT_OCID]",
    include_volumes=True,
    include_ips=True
)

# Response includes:
# - instance name, ID, shape, state
# - private_ip, public_ip, all_private_ips, all_public_ips
# - boot_volumes: [{id, display_name, size_in_gbs, vpus_per_gb, ...}]
# - block_volumes: [{id, display_name, size_in_gbs, vpus_per_gb, ...}]
# - total_volume_size_gb
```

### Get Instance Costs

```python
# Get costs for an instance including volumes
cost_info = get_instance_cost(
    instance_id="[Link to Secure Variable: OCI_INSTANCE_OCID]",
    time_window="30d",  # or "7d", "1h", etc.
    include_volumes=True
)

# Response includes:
# {
#   "costs": {
#     "compute": 45.50,
#     "block_storage": 12.30,
#     "total": 57.80,
#     "currency": "USD"
#   },
#   "volume_costs": {
#     "[Link to Secure Variable: OCI_BOOT_VOLUME_OCID]": {"name": "boot-vol-1", "cost": 5.20, "type": "boot_volume"},
#     "[Link to Secure Variable: OCI_BLOCK_VOLUME_OCID]": {"name": "data-vol-1", "cost": 7.10, "type": "block_volume"}
#   }
# }
```

### Get Comprehensive Details

```python
# Get everything in one call
details = get_comprehensive_instance_details(
    instance_id="[Link to Secure Variable: OCI_INSTANCE_OCID]",
    include_volumes=True,
    include_ips=True,
    include_costs=True,
    cost_time_window="30d"
)
```

### Start/Stop Instances

```python
# Start an instance
result = start_instance(instance_id="[Link to Secure Variable: OCI_INSTANCE_OCID]")

# Stop an instance
result = stop_instance(instance_id="[Link to Secure Variable: OCI_INSTANCE_OCID]")
```

## Chat/Slack Integration Workflow

### Typical User Flow

1. **Initial Query**: "Show me all instances in compartment X"
   - Use `list_instances(compartment_id="...", include_volumes=True, include_ips=True)`
   - Returns: instance names, IPs, configuration, volumes

2. **Follow-up Questions**:
   - "What's the cost of instance Y?" → `get_instance_cost(instance_id="...")`
   - "Start instance Z" → `start_instance(instance_id="...")`
   - "Stop instance W" → `stop_instance(instance_id="...")`
   - "Show me details for instance V" → `get_comprehensive_instance_details(instance_id="...")`

3. **Cost Analysis**:
   - "Show costs for all instances" → Iterate through instances and call `get_instance_cost` for each

## Performance Optimizations

1. **Caching**: All queries are cached to minimize API calls
2. **Optional Fields**: Volumes and IPs can be excluded for faster queries
3. **Batch Operations**: Volume attachments are fetched efficiently per instance
4. **Error Handling**: Graceful degradation if volume/IP queries fail

## Architecture Notes

### Modular Design

- `_get_instance_volumes()`: Black box function for volume retrieval
- `_get_instance_ips()`: Black box function for IP retrieval
- `_fetch_instances()`: Core instance fetching with optional enhancements
- `get_instance_cost()`: Cost calculation with volume support
- `get_comprehensive_instance_details()`: Unified interface for all details

### Error Handling

All functions handle errors gracefully:
- Missing volumes return empty arrays
- Failed IP queries return null values
- Cost queries return error objects on failure
- All errors are logged with OpenTelemetry tracing

## API Reference

### list_instances

```python
list_instances(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    include_volumes: bool = True,
    include_ips: bool = True,
    force_refresh: bool = False
) -> List[Dict]
```

### get_instance_cost

```python
get_instance_cost(
    instance_id: str,
    time_window: str = "30d",
    include_volumes: bool = True
) -> Dict
```

### get_comprehensive_instance_details

```python
get_comprehensive_instance_details(
    instance_id: str,
    include_volumes: bool = True,
    include_ips: bool = True,
    include_costs: bool = False,
    cost_time_window: str = "30d"
) -> Dict[str, Any]
```

## Response Format

### Instance Object Structure

```json
{
  "id": "[Link to Secure Variable: OCI_INSTANCE_OCID]",
  "display_name": "my-instance",
  "lifecycle_state": "RUNNING",
  "shape": "VM.Standard.E4.Flex",
  "shape_config": {
    "ocpus": 2,
    "memory_in_gbs": 16,
    "baseline_ocpu_utilization": "BASELINE_1_1"
  },
  "availability_domain": "AD-1",
  "compartment_id": "[Link to Secure Variable: OCI_COMPARTMENT_OCID]",
  "region": "us-ashburn-1",
  "time_created": "2024-01-15T10:30:00Z",
  "private_ip": "10.0.1.5",
  "public_ip": "203.0.113.10",
  "all_private_ips": ["10.0.1.5"],
  "all_public_ips": ["203.0.113.10"],
  "boot_volumes": [
    {
      "id": "[Link to Secure Variable: OCI_BOOT_VOLUME_OCID]",
      "display_name": "boot-vol-1",
      "size_in_gbs": 50,
      "vpus_per_gb": 10,
      "lifecycle_state": "AVAILABLE",
      "attachment_id": "[Link to Secure Variable: OCI_BOOT_VOLUME_ATTACHMENT_OCID]",
      "attachment_type": "iscsi"
    }
  ],
  "block_volumes": [
    {
      "id": "[Link to Secure Variable: OCI_BLOCK_VOLUME_OCID]",
      "display_name": "data-vol-1",
      "size_in_gbs": 100,
      "vpus_per_gb": 20,
      "lifecycle_state": "AVAILABLE",
      "attachment_id": "[Link to Secure Variable: OCI_VOLUME_ATTACHMENT_OCID]",
      "attachment_type": "iscsi"
    }
  ],
  "total_volume_size_gb": 150
}
```

## Testing

To test the enhanced functionality:

```bash
# Test listing instances with volumes
python -m mcp_servers.compute.server

# In another terminal, use MCP client to call:
# list_instances(compartment_id="[Link to Secure Variable: OCI_COMPARTMENT_OCID]", include_volumes=True)
```

## Future Enhancements

Potential improvements:
1. Batch cost queries for multiple instances
2. Volume cost estimation based on size and VPU configuration
3. Instance lifecycle cost projections
4. Cost alerts and recommendations
