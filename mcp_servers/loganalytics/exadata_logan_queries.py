#!/usr/bin/env python3
"""
Best Logan (Log Analytics) Queries for Exadata Costs

This module provides the most effective Log Analytics queries for extracting
and analyzing Oracle Exadata costs from OCI Log Analytics.
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class LoganQuery:
    """Logan query definition"""
    name: str
    description: str
    query: str
    use_case: str
    time_range: str = "30d"
    expected_fields: List[str] = None

class ExadataLoganQueries:
    """Best practices Logan queries for Exadata cost analysis"""

    def __init__(self):
        self.queries = self._build_query_catalog()

    def _build_query_catalog(self) -> Dict[str, LoganQuery]:
        """Build catalog of optimized Logan queries for Exadata"""

        queries = {}

        # 1. Basic Exadata Cost Extraction (Your Working Query Enhanced)
        basic_cost_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| fields product_compartmentName, cost_attributedCost, product_resourceId,
'tags_orcl-cloud.parent_resource_id_1', 'tags_orcl-cloud.resource_name',
product_service, 'Log Date'
| sort cost_attributedCost desc"""

        queries["basic_exadata_costs"] = LoganQuery(
            name="Basic Exadata Cost Extraction",
            description="Extract all Exadata pluggable database costs with resource details",
            query=basic_cost_query,
            use_case="Daily cost monitoring and basic analysis",
            expected_fields=["product_compartmentName", "cost_attributedCost", "product_resourceId"]
        )

        # 2. Exadata VM Cluster Cost Aggregation
        vm_cluster_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%vmcluster%'
and cost_attributedCost > 0
| stats sum(cost_attributedCost) as total_cluster_cost,
count as database_count,
avg(cost_attributedCost) as avg_db_cost,
max(cost_attributedCost) as max_db_cost
by product_compartmentName, 'tags_orcl-cloud.parent_resource_id_1'
| sort total_cluster_cost desc"""

        queries["vm_cluster_aggregation"] = LoganQuery(
            name="Exadata VM Cluster Cost Aggregation",
            description="Aggregate costs by VM cluster and compartment",
            query=vm_cluster_query,
            use_case="Cluster-level cost analysis and optimization",
            expected_fields=["total_cluster_cost", "database_count", "product_compartmentName"]
        )

        # 3. Exadata Service Level Cost Analysis
        service_level_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and (product_resourceId like '%exadata%' or product_resourceId like '%pluggabledatabase%')
and cost_attributedCost > 0
| eval exadata_service_type = case(
    product_resourceId like '%vmcluster%', "VM Cluster",
    product_resourceId like '%pluggabledatabase%', "Pluggable Database",
    product_resourceId like '%exadata%', "Exadata Infrastructure",
    "Other Database Service"
)
| stats sum(cost_attributedCost) as total_cost, count as resource_count
by exadata_service_type, product_compartmentName
| sort total_cost desc"""

        queries["service_level_analysis"] = LoganQuery(
            name="Exadata Service Level Cost Analysis",
            description="Break down costs by Exadata service types",
            query=service_level_query,
            use_case="Understanding cost distribution across Exadata services",
            expected_fields=["exadata_service_type", "total_cost", "resource_count"]
        )

        # 4. Daily Exadata Cost Trends
        daily_trend_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| bucket 'Log Date' by 1d
| stats sum(cost_attributedCost) as daily_cost,
count as daily_db_count,
avg(cost_attributedCost) as daily_avg_cost
by 'Log Date', product_compartmentName
| sort 'Log Date' desc, daily_cost desc"""

        queries["daily_cost_trends"] = LoganQuery(
            name="Daily Exadata Cost Trends",
            description="Track daily cost patterns and identify anomalies",
            query=daily_trend_query,
            use_case="Cost trend analysis and anomaly detection",
            time_range="7d",
            expected_fields=["Log Date", "daily_cost", "daily_db_count"]
        )

        # 5. High-Cost Exadata Database Identification
        high_cost_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost >= 3.0
| stats sum(cost_attributedCost) as total_high_cost,
count as high_cost_count,
avg(cost_attributedCost) as avg_high_cost,
max(cost_attributedCost) as peak_cost
by product_compartmentName, product_resourceId, 'tags_orcl-cloud.resource_name'
| sort total_high_cost desc
| head 20"""

        queries["high_cost_databases"] = LoganQuery(
            name="High-Cost Exadata Database Identification",
            description="Identify databases with costs ≥$3 for optimization",
            query=high_cost_query,
            use_case="Cost optimization targeting and budget management",
            expected_fields=["total_high_cost", "high_cost_count", "product_resourceId"]
        )

        # 6. Exadata Cost by Region/Availability Domain
        regional_cost_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| eval region = case(
    'tags_orcl-cloud.parent_resource_id_1' like '%eu-frankfurt%', "Frankfurt",
    'tags_orcl-cloud.parent_resource_id_1' like '%eu-milan%', "Milan",
    'tags_orcl-cloud.parent_resource_id_1' like '%eu-athens%', "Athens",
    'tags_orcl-cloud.parent_resource_id_1' like '%eu-paris%', "Paris",
    'tags_orcl-cloud.parent_resource_id_1' like '%eu-', "Other EU",
    "Unknown"
)
| stats sum(cost_attributedCost) as regional_cost,
count as db_count,
avg(cost_attributedCost) as avg_db_cost
by region, product_compartmentName
| sort regional_cost desc"""

        queries["regional_cost_analysis"] = LoganQuery(
            name="Exadata Cost by Region Analysis",
            description="Analyze cost distribution across OCI regions",
            query=regional_cost_query,
            use_case="Regional cost optimization and capacity planning",
            expected_fields=["region", "regional_cost", "db_count"]
        )

        # 7. Exadata Resource Utilization Cost Analysis
        utilization_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| stats sum(cost_attributedCost) as total_cost,
count as usage_days,
avg(cost_attributedCost) as avg_daily_cost,
min(cost_attributedCost) as min_cost,
max(cost_attributedCost) as max_cost,
stddev(cost_attributedCost) as cost_variance
by product_resourceId, 'tags_orcl-cloud.resource_name', product_compartmentName
| eval utilization_pattern = case(
    cost_variance < 0.5, "Stable",
    cost_variance > 2.0, "Highly Variable",
    "Moderate Variance"
)
| eval cost_efficiency = case(
    avg_daily_cost < 1.0, "Efficient",
    avg_daily_cost > 3.0, "Expensive",
    "Moderate"
)
| sort total_cost desc"""

        queries["utilization_analysis"] = LoganQuery(
            name="Exadata Resource Utilization Cost Analysis",
            description="Analyze cost patterns and resource efficiency",
            query=utilization_query,
            use_case="Resource optimization and utilization planning",
            expected_fields=["total_cost", "utilization_pattern", "cost_efficiency"]
        )

        # 8. Exadata Cost Anomaly Detection
        anomaly_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| bucket 'Log Date' by 1d
| stats avg(cost_attributedCost) as daily_avg_cost,
sum(cost_attributedCost) as daily_total_cost
by 'Log Date', product_compartmentName
| eventstats avg(daily_total_cost) as baseline_cost,
stddev(daily_total_cost) as cost_stddev
by product_compartmentName
| eval cost_anomaly = case(
    daily_total_cost > (baseline_cost + (2 * cost_stddev)), "High Anomaly",
    daily_total_cost < (baseline_cost - (2 * cost_stddev)), "Low Anomaly",
    daily_total_cost > (baseline_cost + cost_stddev), "Elevated",
    "Normal"
)
| where cost_anomaly != "Normal"
| sort 'Log Date' desc, daily_total_cost desc"""

        queries["cost_anomaly_detection"] = LoganQuery(
            name="Exadata Cost Anomaly Detection",
            description="Detect unusual cost spikes or drops using statistical analysis",
            query=anomaly_query,
            use_case="Automated cost monitoring and alerting",
            time_range="14d",
            expected_fields=["Log Date", "cost_anomaly", "daily_total_cost"]
        )

        # 9. Compartment Budget vs Actual Analysis
        budget_analysis_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| stats sum(cost_attributedCost) as actual_spend,
count as db_count,
avg(cost_attributedCost) as avg_db_cost,
max(cost_attributedCost) as max_db_cost
by product_compartmentName
| eval monthly_projected = actual_spend * (30 / 30)
| eval budget_status = case(
    actual_spend > 100, "Over Budget",
    actual_spend > 75, "Near Budget Limit",
    actual_spend > 50, "Moderate Spend",
    "Under Budget"
)
| eval optimization_priority = case(
    max_db_cost > 5.0, "High Priority",
    avg_db_cost > 2.0, "Medium Priority",
    "Low Priority"
)
| sort actual_spend desc"""

        queries["budget_analysis"] = LoganQuery(
            name="Compartment Budget vs Actual Analysis",
            description="Compare actual spending against budget thresholds",
            query=budget_analysis_query,
            use_case="Budget management and financial governance",
            expected_fields=["actual_spend", "budget_status", "optimization_priority"]
        )

        # 10. Exadata Database Lifecycle Cost Analysis
        lifecycle_query = """'Upload Name' = vf_5 and 'Log Source' = VF_budget_noFocus
and product_service = database
and product_resourceId like '%pluggabledatabase%'
and cost_attributedCost > 0
| bucket 'Log Date' by 1w
| stats sum(cost_attributedCost) as weekly_cost,
count as active_days
by 'Log Date', product_resourceId, 'tags_orcl-cloud.resource_name'
| eventstats avg(weekly_cost) as avg_weekly_cost by product_resourceId
| eval cost_trend = case(
    weekly_cost > (avg_weekly_cost * 1.2), "Increasing",
    weekly_cost < (avg_weekly_cost * 0.8), "Decreasing",
    "Stable"
)
| eval lifecycle_stage = case(
    active_days < 3, "New/Testing",
    active_days = 7, "Production",
    "Partial Usage"
)
| sort 'Log Date' desc, weekly_cost desc"""

        queries["lifecycle_analysis"] = LoganQuery(
            name="Exadata Database Lifecycle Cost Analysis",
            description="Track cost patterns throughout database lifecycle",
            query=lifecycle_query,
            use_case="Lifecycle cost management and resource planning",
            time_range="8w",
            expected_fields=["weekly_cost", "cost_trend", "lifecycle_stage"]
        )

        return queries

    def get_query(self, query_name: str) -> LoganQuery:
        """Get a specific Logan query by name"""
        return self.queries.get(query_name)

    def get_all_queries(self) -> Dict[str, LoganQuery]:
        """Get all available Logan queries"""
        return self.queries

    def get_queries_by_use_case(self, use_case_keyword: str) -> List[LoganQuery]:
        """Get queries matching a specific use case keyword"""
        matching_queries = []
        for query in self.queries.values():
            if use_case_keyword.lower() in query.use_case.lower():
                matching_queries.append(query)
        return matching_queries

    def get_recommended_queries_for_analysis_type(self, analysis_type: str) -> List[str]:
        """Get recommended query names for specific analysis types"""

        recommendations = {
            "basic_cost_monitoring": [
                "basic_exadata_costs",
                "daily_cost_trends",
                "budget_analysis"
            ],
            "optimization": [
                "high_cost_databases",
                "utilization_analysis",
                "service_level_analysis"
            ],
            "anomaly_detection": [
                "cost_anomaly_detection",
                "daily_cost_trends",
                "lifecycle_analysis"
            ],
            "regional_analysis": [
                "regional_cost_analysis",
                "vm_cluster_aggregation",
                "basic_exadata_costs"
            ],
            "comprehensive": [
                "basic_exadata_costs",
                "vm_cluster_aggregation",
                "high_cost_databases",
                "daily_cost_trends",
                "budget_analysis"
            ]
        }

        return recommendations.get(analysis_type, ["basic_exadata_costs"])


def get_best_exadata_logan_queries() -> Dict[str, str]:
    """Get the best Logan queries for Exadata cost analysis

    Returns:
        Dict mapping query names to query strings
    """
    query_catalog = ExadataLoganQueries()
    return {name: query.query for name, query in query_catalog.get_all_queries().items()}


def get_query_recommendations(analysis_goal: str) -> List[Dict[str, str]]:
    """Get query recommendations based on analysis goal

    Args:
        analysis_goal: Type of analysis needed (basic, optimization, anomaly, etc.)

    Returns:
        List of recommended queries with metadata
    """
    query_catalog = ExadataLoganQueries()

    if analysis_goal == "cost_drilldown":
        # For service_cost_drilldown replacement
        recommended_names = [
            "basic_exadata_costs",
            "service_level_analysis",
            "high_cost_databases"
        ]
    elif analysis_goal == "monitoring":
        recommended_names = [
            "daily_cost_trends",
            "cost_anomaly_detection",
            "budget_analysis"
        ]
    elif analysis_goal == "optimization":
        recommended_names = [
            "high_cost_databases",
            "utilization_analysis",
            "regional_cost_analysis"
        ]
    else:
        recommended_names = ["basic_exadata_costs"]

    recommendations = []
    for name in recommended_names:
        query = query_catalog.get_query(name)
        if query:
            recommendations.append({
                "name": query.name,
                "query": query.query,
                "description": query.description,
                "use_case": query.use_case,
                "time_range": query.time_range
            })

    return recommendations


if __name__ == "__main__":
    # Example usage
    catalog = ExadataLoganQueries()

    print("=== Best Logan Queries for Exadata Costs ===")
    for name, query in catalog.get_all_queries().items():
        print(f"\n{query.name}:")
        print(f"Description: {query.description}")
        print(f"Use Case: {query.use_case}")
        print(f"Query: {query.query[:100]}...")

    print(f"\nTotal queries available: {len(catalog.get_all_queries())}")