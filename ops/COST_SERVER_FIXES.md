# OCI Usage API Fixes for Cost MCP Server

## Issues Identified and Fixed

### 1. ❌ **InvalidParameter: filter.dimensions[0].value must not be null**

**Root Cause:** Incorrect filter dimension structure
- **Before:** `{"dimensionKey": "service", "values": ["Compute"]}`
- **After:** `{"key": "service", "value": "Compute"}`

**Files Fixed:**
- `mcp_servers/cost/server.py`: Updated `_aggregate_usage_across_compartments()` function
- `mcp_servers/cost/server.py`: Fixed `service_cost_drilldown()` function
- `mcp_servers/cost/server.py`: Fixed `object_storage_costs_and_tiering()` function

### 2. ❌ **InvalidParameter: groupBy must be null when groupByTagKey isn't empty**

**Root Cause:** API constraint violation - cannot use both `group_by` and `group_by_tag` simultaneously

**Files Fixed:**
- `mcp_servers/cost/finopsai/tools/usage_queries.py`: Added conflict resolution logic
- `mcp_servers/cost/server.py`: Fixed `cost_by_tag_key_value()` function

**Fix Logic:**
```python
# When group_by_tag is specified, group_by must be null
group_by_param = None if (q.group_by_tag and len(q.group_by_tag) > 0) else (q.group_by or [])
```

### 3. 🔧 **Data Accuracy Improvements**

**Field Access Standardization:**
- Handle both `computedAmount` and `computed_amount` field names
- Handle both `timeUsageStarted` and `time_usage_started` field names
- Improved null/empty value handling

**Files Updated:**
- `mcp_servers/cost/server.py`: Standardized field access patterns across all functions

## Code Changes Summary

### Filter Structure Fix
```python
# OLD (Incorrect)
{
    "dimensions": [
        {"dimensionKey": "service", "values": ["Compute"]}
    ]
}

# NEW (Correct)
{
    "operator": "AND",
    "dimensions": [
        {"key": "service", "value": "Compute"}
    ]
}
```

### Group By Conflict Resolution
```python
# OLD (Causes conflict)
UsageQuery(
    group_by=["service"],
    group_by_tag=[{"namespace": "FinOps", "key": "CostCenter"}]
)

# NEW (Resolved)
UsageQuery(
    group_by=None,  # Must be null when group_by_tag is used
    group_by_tag=[{"namespace": "FinOps", "key": "CostCenter"}]
)
```

### Field Access Standardization
```python
# OLD (Single field name)
amt = float(it.get("computedAmount", 0))

# NEW (Handles both possible field names)
amt = float(it.get("computedAmount") or it.get("computed_amount", 0))
```

## Functions Fixed

1. **`service_cost_drilldown()`** - Fixed filter dimensions structure
2. **`cost_by_compartment_daily()`** - Improved field access patterns
3. **`cost_by_tag_key_value()`** - Fixed group_by vs group_by_tag conflict
4. **`object_storage_costs_and_tiering()`** - Fixed filter dimensions structure
5. **`monthly_trend_forecast()`** - Standardized field access
6. **`top_cost_spikes_explain()`** - Standardized field access
7. **`_aggregate_usage_across_compartments()`** - Fixed filter structure and removed duplicate

## Testing

Run the validation test:
```bash
cd ops
python test-cost-server-fixes.py
```

Expected results after restart:
- ✅ No more `InvalidParameter` errors for filter dimensions
- ✅ No more `groupBy must be null` errors
- ✅ Consistent cost data across API response format variations
- ✅ Proper handling of null/empty values

## Next Steps

1. Restart the cost MCP server
2. Test the previously failing tools:
   - `service_cost_drilldown`
   - `cost_by_compartment_daily`
   - `cost_by_tag_key_value`
3. Validate cost data accuracy and period formatting

The fixes ensure compliance with OCI Usage API requirements and improve data reliability across different API response formats.