# Best Logan (Log Analytics) Queries for Exadata Costs

## Problem Solved
The `service_cost_drilldown` tool was trying to use the OCI Usage API and failing with "Unable to process JSON input" errors. For Exadata cost analysis, **Logan (Log Analytics) queries are more appropriate and reliable**.

## New MCP Tool Available
**`oci_loganalytics_exadata_cost_drilldown`** - Direct replacement for failing Usage API calls

## 🎯 **Top 3 Recommended Logan Queries for Exadata**

### 1. **Basic Exadata Cost Extraction** (Your Working Query Enhanced)
```sql
'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| fields product_compartmentName, cost_attributedCost, product_resourceId,
'tags_orcl-cloud.parent_resource_id_1', 'tags_orcl-cloud.resource_name',
product_service, 'Log Date'
| sort cost_attributedCost desc
```
**Use Case**: Daily cost monitoring and basic analysis
**Time Range**: 30d

### 2. **High-Cost Database Identification** (Cost Optimization)
```sql
'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost >= 3.0
| stats sum(cost_attributedCost) as total_high_cost,
count as high_cost_count,
avg(cost_attributedCost) as avg_high_cost,
max(cost_attributedCost) as peak_cost
by product_compartmentName, product_resourceId, 'tags_orcl-cloud.resource_name'
| sort total_high_cost desc
| head 20
```
**Use Case**: Identify databases with costs ≥$3 for optimization
**Time Range**: 30d

### 3. **VM Cluster Cost Aggregation** (Infrastructure Level)
```sql
'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%vmcluster%'
and cost_attributedCost > 0
| stats sum(cost_attributedCost) as total_cluster_cost,
count as database_count,
avg(cost_attributedCost) as avg_db_cost,
max(cost_attributedCost) as max_db_cost
by product_compartmentName, 'tags_orcl-cloud.parent_resource_id_1'
| sort total_cluster_cost desc
```
**Use Case**: Cluster-level cost analysis and optimization
**Time Range**: 30d

## 📊 **All Available Logan Queries (10 Total)**

| Query Name | Use Case | Best For |
|------------|----------|----------|
| `basic_exadata_costs` | Daily cost monitoring | General analysis |
| `vm_cluster_aggregation` | Cluster-level analysis | Infrastructure teams |
| `service_level_analysis` | Service type breakdown | Architecture planning |
| `daily_cost_trends` | Trend analysis | Anomaly detection |
| `high_cost_databases` | Cost optimization | FinOps teams |
| `regional_cost_analysis` | Regional distribution | Multi-region deployments |
| `utilization_analysis` | Resource efficiency | Capacity planning |
| `cost_anomaly_detection` | Automated monitoring | Operations teams |
| `budget_analysis` | Budget management | Financial governance |
| `lifecycle_analysis` | Database lifecycle | DevOps teams |

## 🔧 **How to Use Instead of service_cost_drilldown**

### Instead of this (failing):
```bash
service_cost_drilldown(target_service="database")
```

### Use this (working):
```bash
oci_loganalytics_exadata_cost_drilldown(
    analysis_type="cost_drilldown",
    compartment_id="your-compartment-id",
    time_range="30d"
)
```

### Or run specific queries:
```bash
oci_loganalytics_exadata_cost_drilldown(
    query_name="basic_exadata_costs",
    compartment_id="your-compartment-id",
    time_range="30d"
)
```

## 📈 **Analysis Types Available**

| Analysis Type | Queries Included | Best For |
|---------------|------------------|----------|
| `basic_cost_monitoring` | Basic costs, daily trends, budget analysis | Regular monitoring |
| `optimization` | High-cost DBs, utilization, service levels | Cost optimization |
| `anomaly_detection` | Cost anomalies, trends, lifecycle | Operations |
| `regional_analysis` | Regional costs, VM clusters, basic costs | Multi-region |
| `cost_drilldown` | Basic costs, service levels, high-cost DBs | Detailed analysis |

## ✅ **Key Benefits of Logan Queries**

1. **No Usage API Issues**: Bypasses JSON processing errors
2. **Real Cost Data**: Direct access to your actual cost logs
3. **Flexible Filtering**: Filter by compartment, resource, time
4. **Rich Metadata**: Access to tags, resource names, compartments
5. **Performance Optimized**: Queries optimized for Logan syntax
6. **Custom Analysis**: 10 different query types for various use cases

## 🚀 **Quick Start Examples**

### Get basic Exadata costs:
```bash
oci_loganalytics_exadata_cost_drilldown(
    analysis_type="basic_cost_monitoring",
    compartment_id="ocid1.compartment.oc1..abc123",
    time_range="7d"
)
```

### Find high-cost databases:
```bash
oci_loganalytics_exadata_cost_drilldown(
    query_name="high_cost_databases",
    compartment_id="ocid1.compartment.oc1..abc123"
)
```

### Regional cost analysis:
```bash
oci_loganalytics_exadata_cost_drilldown(
    analysis_type="regional_analysis",
    compartment_id="ocid1.compartment.oc1..abc123",
    time_range="30d"
)
```

## 📝 **Note**
These Logan queries work directly with your Log Analytics data and avoid the Usage API JSON processing issues. They provide more detailed and flexible cost analysis specifically for Exadata resources.