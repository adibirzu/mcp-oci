# OCI Cost MCP Server - Comprehensive Testing & Usage Guide

## 🎯 Overview
This guide provides systematic testing procedures and practical usage patterns for OCI Cost MCP servers, designed for FinOps practitioners and cost optimization specialists.

## 🛠️ Server Architecture

### Enhanced Cost Server (oci-mcp-cost-enhanced)
**Location**: `/Users/abirzu/dev/mcp-oci/mcp_servers/cost/server.py`
**Status**: ✅ **WORKING** - Fixed serialization issues
**Features**: 15 total tools (12 FinOpsAI + 3 Legacy)

### Standalone OCI Cost MCP
**Status**: ✅ **WORKING** - Production ready
**Features**: Reliable cost summaries, usage breakdown, anomaly detection

---

## 🧪 Systematic Testing Protocol

### Phase 1: Basic Connectivity Tests

#### Test 1: Cost Summary Validation
```
Tool: Get cost summary
Purpose: Verify OCI API connectivity and basic cost retrieval
Expected: Total cost amount with currency and time period
Success Criteria: Non-zero cost data with proper formatting
```

#### Test 2: Service Breakdown Analysis
```
Tool: Get usage breakdown
Purpose: Validate detailed service cost attribution
Expected: List of services with individual cost amounts
Success Criteria: Multiple services listed with costs > 0
```

#### Test 3: Anomaly Detection
```
Tool: Detect cost anomaly
Purpose: Test statistical analysis capabilities
Expected: Statistical analysis of cost patterns
Success Criteria: Anomaly detection results or "no anomalies found"
```

### Phase 2: Enhanced FinOpsAI Tools Testing

#### Test 4: Monthly Trend Forecasting
```
Tool: monthly_trend_forecast
Purpose: Test advanced trend analysis and forecasting
Parameters: tenancy_ocid, months_back=6
Expected: Monthly cost series with trend direction and forecast
Success Criteria: No serialization errors, meaningful trend data
```

#### Test 5: Service Cost Drilldown
```
Tool: service_cost_drilldown
Purpose: Test hierarchical cost analysis
Parameters: tenancy_ocid, time_start, time_end, top_n=10
Expected: Top services with compartment breakdowns
Success Criteria: Services ranked by cost with compartment details
```

#### Test 6: FOCUS ETL Health Check
```
Tool: focus_etl_healthcheck
Purpose: Verify FOCUS compliance reporting
Parameters: tenancy_ocid, days_back=14
Expected: Daily FOCUS file presence status
Success Criteria: List of dates with present/absent status
```

### Phase 3: Advanced Analytics Testing

#### Test 6.1: Tagging Rules (Tag Defaults)
```
Tool: list_tag_defaults
Purpose: Verify tag default rules for cost attribution policies
Parameters: compartment_id, include_children=true
Expected: Tag default rules list
Success Criteria: Rules include tag definition IDs and compartments
```

#### Test 6.2: Resource-Level Cost
```
Tool: cost_by_resource
Purpose: Break down spend by resource ID/name
Parameters: tenancy_ocid, time_start, time_end, service_name (optional)
Expected: Resource-level cost rows
Success Criteria: Costs aggregated by resource with currency
```

#### Test 6.3: Database Cost (ADB)
```
Tool: cost_by_database
Purpose: Break down spend by database resources
Parameters: tenancy_ocid, time_start, time_end, database_name_contains (optional)
Expected: Database-level cost rows
Success Criteria: Database costs scoped to ADB service by default
```

#### Test 6.4: PDB Cost (Best-effort)
```
Tool: cost_by_pdb
Purpose: Estimate spend by PDB name
Parameters: tenancy_ocid, time_start, time_end, pdb_name_contains
Expected: PDB-level cost rows
Success Criteria: PDB names matched from resourceName fields
```

#### Test 7: Cost Spike Detection
```
Tool: top_cost_spikes_explain
Purpose: Identify and explain cost anomalies
Parameters: tenancy_ocid, time_start, time_end, top_n=5
Expected: Day-over-day cost spikes with explanations
Success Criteria: Spike events with service/compartment attribution
```

#### Test 8: Unit Economics Analysis
```
Tool: per_compartment_unit_cost
Purpose: Calculate unit costs by compartment
Parameters: tenancy_ocid, time_start, time_end, unit="OCPU_HOUR"
Expected: Unit cost calculations per compartment
Success Criteria: Cost per unit metrics for compute resources
```

#### Test 9: Budget vs Forecast Analysis
```
Tool: forecast_vs_universal_credits
Purpose: Compare forecasted spend against credits
Parameters: tenancy_ocid, months_ahead=1, credits_committed=50000
Expected: Forecast vs credits comparison with risk assessment
Success Criteria: Risk categorization (NEUTRAL/OVER/UNDER) with analysis
```

---

## 📊 FinOps Practitioner Usage Patterns

### Daily Operations Workflow

#### Morning Cost Review (5 minutes)
1. **Get cost summary** - Last 7 days overview
2. **Get usage breakdown** - Identify top spending services
3. **Detect cost anomaly** - Check for unusual spending patterns

#### Weekly Analysis (15 minutes)
1. **monthly_trend_forecast** - Understand spending trends
2. **service_cost_drilldown** - Deep dive into top services
3. **top_cost_spikes_explain** - Investigate any cost spikes

#### Monthly Strategic Review (30 minutes)
1. **forecast_vs_universal_credits** - Credit utilization planning
2. **per_compartment_unit_cost** - Unit economics optimization
3. **focus_etl_healthcheck** - Compliance and reporting verification

### Cost Optimization Scenarios

#### Scenario 1: Budget Overrun Investigation
```
1. Get cost summary (current period vs budget)
2. Service cost drilldown (identify major contributors)
3. Top cost spikes explain (find unusual spending)
4. Per compartment unit cost (optimize resource allocation)
```

#### Scenario 2: Forecasting and Planning
```
1. Monthly trend forecast (understand patterns)
2. Forecast vs universal credits (plan credit usage)
3. Service cost drilldown (plan service allocation)
4. FOCUS ETL healthcheck (ensure data quality)
```

#### Scenario 3: Cost Anomaly Response
```
1. Detect cost anomaly (confirm unusual activity)
2. Top cost spikes explain (understand root causes)
3. Service cost drilldown (compartment-level analysis)
4. Get usage breakdown (service-level details)
```

---

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Issue: "No result received from client-side tool execution"
**Cause**: Tool timeout or parameter validation error
**Solution**:
- Verify OCI credentials are properly configured
- Check tenancy_ocid parameter format
- Reduce date range for large data queries

#### Issue: FinOpsAI tools returning serialization errors
**Status**: ✅ **FIXED** - Updated to use safe serialization
**Solution**: Enhanced server now includes robust error handling

#### Issue: Empty or zero cost data
**Cause**: Wrong compartment scope or time period
**Solution**:
- Verify tenancy_ocid is correct
- Use broader date ranges (last 30 days)
- Check if Usage API is enabled in OCI

#### Issue: Budget analysis tools failing
**Cause**: Missing budget configuration or permissions
**Solution**:
- Create budgets in OCI console first
- Ensure proper IAM policies for Budget API access
- Use get_cost_summary as fallback

---

## 📈 Expected Results Reference

### Database-Heavy Workload (Your Current Profile)
- **Total Cost**: ~₪18,890 (7 days) = ~₪80,958 (monthly projection)
- **Top Service**: Database (₪48,067, 57% of total)
- **Secondary Services**: Block Storage, Compute
- **Budget Status**: 304% overrun detected
- **Optimization Priority**: Database cost management

### Typical Cost Distribution Patterns
- **Compute-Heavy**: 40-60% Compute, 20-30% Storage, 10-20% Network
- **Storage-Heavy**: 50-70% Object Storage, 20-30% Database, 10-20% Compute
- **Database-Heavy**: 50-70% Database, 15-25% Compute, 10-20% Storage

---

## 🚀 Advanced Usage Tips

### Power User Techniques

1. **Combine Multiple Tools**: Use service_cost_drilldown + per_compartment_unit_cost for comprehensive analysis
2. **Time Series Analysis**: Run monthly_trend_forecast with different months_back values (3, 6, 12)
3. **Comparative Analysis**: Use cost_by_tag_key_value for project-based cost attribution
4. **Proactive Monitoring**: Set up regular top_cost_spikes_explain runs for early anomaly detection

### Automation Opportunities
- Schedule daily cost summaries
- Create alerting based on anomaly detection
- Automate monthly trend reports
- Set up FOCUS compliance monitoring

---

## ✅ Success Metrics

### Tool Performance Indicators
- **Response Time**: < 30 seconds for most queries
- **Data Accuracy**: Matches OCI Console within 5%
- **Coverage**: All major cost categories represented
- **Reliability**: < 1% error rate for standard queries

### Business Value Delivered
- **Cost Visibility**: Real-time spending insights
- **Trend Analysis**: Predictive cost forecasting
- **Anomaly Detection**: Rapid identification of cost issues
- **Compliance**: FOCUS-compliant reporting capabilities
- **Unit Economics**: Resource efficiency optimization

---

*Generated programmatically - OCI Cost MCP Server Enhanced*
*Last Updated: September 2024*
