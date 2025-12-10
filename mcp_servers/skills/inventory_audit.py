"""
Inventory Audit Skill for MCP-OCI

Provides comprehensive resource discovery, capacity planning, and infrastructure
audit capabilities following the skillz pattern.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .adapters import InventoryClientAdapter

logger = logging.getLogger(__name__)


@dataclass
class ResourceSummary:
    """Summary of a resource type."""
    resource_type: str
    count: int
    regions: List[str] = field(default_factory=list)
    compartments: List[str] = field(default_factory=list)


@dataclass
class CapacityIssue:
    """Represents a capacity concern."""
    severity: str  # "info", "warning", "critical"
    resource_type: str
    issue: str
    recommendation: str
    affected_resources: List[str] = field(default_factory=list)


@dataclass
class AuditFinding:
    """Represents an audit finding."""
    category: str  # "security", "compliance", "optimization", "reliability"
    severity: str  # "low", "medium", "high", "critical"
    finding: str
    remediation: str
    affected_count: int = 0


class InventoryAuditSkill:
    """
    Inventory Audit Skill - Orchestrates inventory tools for comprehensive audits.
    
    Capabilities:
    - Full infrastructure discovery
    - Resource inventory and tagging compliance
    - Capacity analysis and planning
    - Change detection (diff-based)
    - High availability assessment
    """
    
    SKILL_NAME = "inventory-audit"
    SKILL_VERSION = "1.0.0"
    
    def __init__(self, client: Optional[InventoryClientAdapter] = None):
        """
        Initialize the Inventory Audit Skill.
        
        Args:
            client: Optional pre-configured InventoryClientAdapter
        """
        self.client = client or InventoryClientAdapter()
    
    def run_full_discovery(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None,
        limit_per_type: int = 50
    ) -> Dict[str, Any]:
        """
        Run full infrastructure discovery.
        
        Args:
            compartment_id: Optional compartment to scope discovery
            region: Optional region to scope discovery
            limit_per_type: Maximum resources per type
            
        Returns:
            Complete inventory of discovered resources
        """
        try:
            # Get comprehensive discovery
            discovery = self.client.list_all_discovery(
                compartment_id=compartment_id,
                region=region,
                limit_per_type=limit_per_type
            )
            
            if "error" in discovery:
                return discovery
            
            # Analyze discovery results
            resource_counts = self._count_resources(discovery)
            health_assessment = self._assess_infrastructure_health(discovery)
            tagging_compliance = self._check_tagging_compliance(discovery)
            
            return {
                "discovery_type": "full_infrastructure",
                "timestamp": datetime.now().isoformat(),
                "scope": {
                    "compartment_id": compartment_id,
                    "region": region
                },
                "resource_summary": resource_counts,
                "total_resources": sum(r.get("count", 0) for r in resource_counts),
                "health_assessment": health_assessment,
                "tagging_compliance": tagging_compliance,
                "raw_discovery": discovery,
                "recommendations": self._generate_discovery_recommendations(discovery, health_assessment)
            }
            
        except Exception as e:
            logger.error(f"Error running discovery: {e}")
            return {"error": str(e)}
    
    def _count_resources(self, discovery: Dict) -> List[Dict]:
        """Count resources by type from discovery."""
        counts = []
        
        resource_types = [
            ("vcns", "VCN"),
            ("subnets", "Subnet"),
            ("security_lists", "Security List"),
            ("instances", "Compute Instance"),
            ("load_balancers", "Load Balancer"),
            ("functions_apps", "Functions Application"),
            ("streams", "Streaming Stream")
        ]
        
        for key, display_name in resource_types:
            if key in discovery:
                items = discovery[key].get("items", [])
                count = len(items)
                
                # Extract unique compartments and regions
                compartments = set()
                regions = set()
                for item in items:
                    if "compartment_id" in item:
                        compartments.add(item["compartment_id"])
                    if "region" in item:
                        regions.add(item["region"])
                
                counts.append({
                    "type": display_name,
                    "key": key,
                    "count": count,
                    "unique_compartments": len(compartments),
                    "unique_regions": len(regions)
                })
        
        return sorted(counts, key=lambda x: x["count"], reverse=True)
    
    def _assess_infrastructure_health(self, discovery: Dict) -> Dict[str, Any]:
        """Assess overall infrastructure health."""
        issues = []
        status = "healthy"
        
        # Check compute health
        if "instances" in discovery:
            instances = discovery["instances"].get("items", [])
            stopped = [i for i in instances if i.get("lifecycle_state") == "STOPPED"]
            if len(stopped) > len(instances) * 0.3:
                issues.append({
                    "area": "compute",
                    "severity": "warning",
                    "issue": f"{len(stopped)} of {len(instances)} instances are stopped",
                    "recommendation": "Review stopped instances for cost optimization"
                })
                status = "attention_needed"
        
        # Check VCN coverage
        if "vcns" in discovery and "subnets" in discovery:
            vcn_count = len(discovery["vcns"].get("items", []))
            subnet_count = len(discovery["subnets"].get("items", []))
            if vcn_count > 0 and subnet_count / vcn_count < 2:
                issues.append({
                    "area": "networking",
                    "severity": "info",
                    "issue": "Low subnet-to-VCN ratio",
                    "recommendation": "Consider adding subnets for better network segmentation"
                })
        
        # Check load balancer presence
        if "load_balancers" in discovery:
            lb_count = len(discovery["load_balancers"].get("items", []))
            instance_count = len(discovery.get("instances", {}).get("items", []))
            if instance_count > 5 and lb_count == 0:
                issues.append({
                    "area": "availability",
                    "severity": "warning",
                    "issue": "Multiple instances but no load balancers",
                    "recommendation": "Consider adding load balancers for high availability"
                })
                status = "attention_needed"
        
        return {
            "status": status,
            "issues_found": len(issues),
            "issues": issues,
            "checked_areas": ["compute", "networking", "availability"]
        }
    
    def _check_tagging_compliance(self, discovery: Dict) -> Dict[str, Any]:
        """Check tagging compliance across resources."""
        total_resources = 0
        tagged_resources = 0
        resources_by_tag_status = {"tagged": [], "untagged": []}
        
        for resource_type, data in discovery.items():
            if isinstance(data, dict) and "items" in data:
                items = data["items"]
                for item in items:
                    total_resources += 1
                    
                    # Check for tags
                    has_freeform = bool(item.get("freeform_tags", {}))
                    has_defined = bool(item.get("defined_tags", {}))
                    
                    if has_freeform or has_defined:
                        tagged_resources += 1
                        resources_by_tag_status["tagged"].append(resource_type)
                    else:
                        resources_by_tag_status["untagged"].append(resource_type)
        
        compliance_rate = (tagged_resources / total_resources * 100) if total_resources > 0 else 0
        
        # Determine compliance status
        if compliance_rate >= 90:
            status = "compliant"
        elif compliance_rate >= 70:
            status = "partial"
        else:
            status = "non_compliant"
        
        return {
            "status": status,
            "compliance_rate": round(compliance_rate, 2),
            "total_resources": total_resources,
            "tagged_resources": tagged_resources,
            "untagged_count": total_resources - tagged_resources,
            "recommendation": self._get_tagging_recommendation(compliance_rate)
        }
    
    def _get_tagging_recommendation(self, compliance_rate: float) -> str:
        """Get tagging recommendation based on compliance rate."""
        if compliance_rate >= 90:
            return "Excellent tagging compliance. Maintain current standards."
        elif compliance_rate >= 70:
            return "Good tagging compliance. Focus on untagged resources for complete coverage."
        elif compliance_rate >= 50:
            return "Moderate tagging compliance. Implement mandatory tagging policy."
        else:
            return "Poor tagging compliance. Urgent: establish and enforce tagging standards."
    
    def _generate_discovery_recommendations(
        self,
        discovery: Dict,
        health: Dict
    ) -> List[Dict]:
        """Generate recommendations from discovery."""
        recommendations = []
        
        # Add health-based recommendations
        for issue in health.get("issues", []):
            recommendations.append({
                "priority": "high" if issue.get("severity") == "warning" else "medium",
                "category": issue.get("area", "general"),
                "description": issue.get("issue"),
                "action": issue.get("recommendation")
            })
        
        return recommendations
    
    def generate_capacity_report(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive capacity planning report.
        
        Args:
            compartment_id: Optional compartment scope
            region: Optional region scope
            include_metrics: Whether to include performance metrics
            
        Returns:
            Capacity report with analysis and recommendations
        """
        try:
            # Get compute capacity report
            capacity = self.client.generate_compute_capacity_report(
                compartment_id=compartment_id,
                region=region,
                include_metrics=include_metrics,
                output_format="json"
            )
            
            if "error" in capacity:
                return capacity
            
            # Analyze capacity
            utilization_analysis = self._analyze_utilization(capacity)
            shape_analysis = self._analyze_shapes(capacity)
            availability_analysis = self._analyze_availability(capacity)
            
            return {
                "report_type": "capacity_planning",
                "timestamp": capacity.get("timestamp", datetime.now().isoformat()),
                "scope": {
                    "compartment_id": compartment_id,
                    "region": region
                },
                "compute_summary": {
                    "total_instances": capacity.get("total_instances", 0),
                    "by_state": capacity.get("instances_by_state", {}),
                    "by_shape": capacity.get("instances_by_shape", {}),
                    "by_ad": capacity.get("instances_by_ad", {})
                },
                "utilization_analysis": utilization_analysis,
                "shape_analysis": shape_analysis,
                "availability_analysis": availability_analysis,
                "capacity_recommendations": capacity.get("recommendations", []),
                "overall_assessment": self._generate_capacity_assessment(
                    utilization_analysis,
                    shape_analysis,
                    availability_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating capacity report: {e}")
            return {"error": str(e)}
    
    def _analyze_utilization(self, capacity: Dict) -> Dict[str, Any]:
        """Analyze resource utilization."""
        total = capacity.get("total_instances", 0)
        by_state = capacity.get("instances_by_state", {})
        
        running = by_state.get("RUNNING", 0)
        stopped = by_state.get("STOPPED", 0)
        
        # Calculate utilization metrics
        active_rate = (running / total * 100) if total > 0 else 0
        idle_rate = (stopped / total * 100) if total > 0 else 0
        
        return {
            "total_instances": total,
            "running_instances": running,
            "stopped_instances": stopped,
            "active_rate": round(active_rate, 2),
            "idle_rate": round(idle_rate, 2),
            "assessment": self._assess_utilization(active_rate, idle_rate),
            "cost_impact": self._estimate_idle_cost_impact(stopped)
        }
    
    def _assess_utilization(self, active_rate: float, idle_rate: float) -> str:
        """Assess utilization level."""
        if idle_rate > 40:
            return "poor - high percentage of idle resources"
        elif idle_rate > 20:
            return "moderate - consider reviewing stopped instances"
        else:
            return "good - most resources are active"
    
    def _estimate_idle_cost_impact(self, stopped_count: int) -> Dict[str, Any]:
        """Estimate cost impact of idle resources."""
        # Rough estimate: $50/month per stopped instance (storage, etc.)
        monthly_waste = stopped_count * 50
        
        return {
            "stopped_instances": stopped_count,
            "estimated_monthly_waste": monthly_waste,
            "note": "Stopped instances still incur storage costs"
        }
    
    def _analyze_shapes(self, capacity: Dict) -> Dict[str, Any]:
        """Analyze instance shape distribution."""
        by_shape = capacity.get("instances_by_shape", {})
        
        total_shapes = len(by_shape)
        shape_counts = sorted(
            [{"shape": k, "count": v} for k, v in by_shape.items()],
            key=lambda x: x["count"],
            reverse=True
        )
        
        # Check for flex shapes
        flex_shapes = [s for s in by_shape.keys() if "Flex" in s]
        fixed_shapes = [s for s in by_shape.keys() if "Flex" not in s]
        
        return {
            "total_shape_types": total_shapes,
            "shape_distribution": shape_counts[:10],  # Top 10
            "flex_shape_count": len(flex_shapes),
            "fixed_shape_count": len(fixed_shapes),
            "recommendation": self._get_shape_recommendation(flex_shapes, fixed_shapes),
            "optimization_opportunity": len(fixed_shapes) > len(flex_shapes)
        }
    
    def _get_shape_recommendation(
        self,
        flex_shapes: List[str],
        fixed_shapes: List[str]
    ) -> str:
        """Get shape recommendation."""
        if len(fixed_shapes) > len(flex_shapes) * 2:
            return "Consider migrating to Flex shapes for better resource optimization"
        elif len(flex_shapes) > 0:
            return "Good adoption of Flex shapes. Continue migration efforts."
        else:
            return "No Flex shapes detected. Evaluate Flex shapes for cost optimization."
    
    def _analyze_availability(self, capacity: Dict) -> Dict[str, Any]:
        """Analyze availability domain distribution."""
        by_ad = capacity.get("instances_by_ad", {})
        
        ad_count = len(by_ad)
        total_instances = sum(by_ad.values())
        
        # Check distribution
        if ad_count == 0:
            distribution = "unknown"
            risk = "Cannot assess AD distribution"
        elif ad_count == 1:
            distribution = "single_ad"
            risk = "High - all instances in single availability domain"
        else:
            # Check if balanced
            counts = list(by_ad.values())
            max_count = max(counts)
            min_count = min(counts)
            
            if max_count > min_count * 2:
                distribution = "unbalanced"
                risk = "Medium - uneven distribution across ADs"
            else:
                distribution = "balanced"
                risk = "Low - good distribution across ADs"
        
        return {
            "ad_count": ad_count,
            "distribution": by_ad,
            "distribution_type": distribution,
            "risk_assessment": risk,
            "recommendation": self._get_ad_recommendation(ad_count, total_instances)
        }
    
    def _get_ad_recommendation(self, ad_count: int, total_instances: int) -> str:
        """Get availability domain recommendation."""
        if ad_count == 1 and total_instances > 2:
            return "Deploy across multiple ADs for high availability"
        elif ad_count > 1:
            return "Good multi-AD deployment. Ensure critical workloads are distributed."
        else:
            return "Consider availability requirements for your workload"
    
    def _generate_capacity_assessment(
        self,
        utilization: Dict,
        shapes: Dict,
        availability: Dict
    ) -> Dict[str, Any]:
        """Generate overall capacity assessment."""
        scores = {
            "utilization": 1.0 if utilization.get("active_rate", 0) > 80 else 
                          0.7 if utilization.get("active_rate", 0) > 60 else 0.4,
            "shape_optimization": 0.8 if shapes.get("flex_shape_count", 0) > 0 else 0.5,
            "availability": 1.0 if availability.get("distribution_type") == "balanced" else
                          0.6 if availability.get("ad_count", 0) > 1 else 0.3
        }
        
        overall_score = sum(scores.values()) / len(scores)
        
        if overall_score >= 0.8:
            status = "excellent"
        elif overall_score >= 0.6:
            status = "good"
        elif overall_score >= 0.4:
            status = "needs_improvement"
        else:
            status = "critical"
        
        return {
            "overall_score": round(overall_score * 100, 1),
            "status": status,
            "component_scores": {k: round(v * 100, 1) for k, v in scores.items()},
            "summary": self._get_assessment_summary(status, scores)
        }
    
    def _get_assessment_summary(self, status: str, scores: Dict) -> str:
        """Get assessment summary text."""
        lowest = min(scores.items(), key=lambda x: x[1])
        
        summaries = {
            "excellent": "Infrastructure is well-optimized across all dimensions.",
            "good": f"Infrastructure is generally healthy. Focus on improving {lowest[0]}.",
            "needs_improvement": f"Infrastructure needs attention. Priority: {lowest[0]}.",
            "critical": "Infrastructure requires immediate attention across multiple areas."
        }
        
        return summaries.get(status, "Assessment complete.")
    
    def detect_changes(
        self,
        profile: Optional[str] = None,
        regions: Optional[List[str]] = None,
        compartments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect infrastructure changes using ShowOCI diff mode.
        
        Args:
            profile: OCI profile to use
            regions: List of regions to scan
            compartments: List of compartments to scan
            
        Returns:
            Change detection results with diff analysis
        """
        try:
            # Run ShowOCI in diff mode
            result = self.client.run_showoci(
                profile=profile,
                regions=regions,
                compartments=compartments,
                diff_mode=True,
                limit=100
            )
            
            if "error" in result:
                return result
            
            changes_detected = result.get("changes_detected", False)
            diff_text = result.get("diff", "")
            
            # Analyze changes
            change_analysis = self._analyze_diff(diff_text) if changes_detected else None
            
            return {
                "detection_type": "infrastructure_changes",
                "timestamp": datetime.now().isoformat(),
                "changes_detected": changes_detected,
                "change_analysis": change_analysis,
                "raw_diff": diff_text[:5000] if diff_text else None,  # Truncate for response
                "recommendations": self._generate_change_recommendations(change_analysis) if change_analysis else []
            }
            
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            return {"error": str(e)}
    
    def _analyze_diff(self, diff_text: str) -> Dict[str, Any]:
        """Analyze diff output for meaningful changes."""
        if not diff_text:
            return {"total_changes": 0, "changes": []}
        
        # Parse diff for additions and removals
        lines = diff_text.split("\n")
        additions = [l for l in lines if l.startswith("+") and not l.startswith("+++")]
        removals = [l for l in lines if l.startswith("-") and not l.startswith("---")]
        
        return {
            "total_changes": len(additions) + len(removals),
            "additions": len(additions),
            "removals": len(removals),
            "change_types": self._categorize_changes(additions, removals),
            "summary": self._summarize_changes(len(additions), len(removals))
        }
    
    def _categorize_changes(
        self,
        additions: List[str],
        removals: List[str]
    ) -> Dict[str, int]:
        """Categorize changes by type."""
        categories = {
            "compute": 0,
            "networking": 0,
            "storage": 0,
            "database": 0,
            "other": 0
        }
        
        keywords = {
            "compute": ["instance", "compute", "vm"],
            "networking": ["vcn", "subnet", "security", "network", "load balancer"],
            "storage": ["bucket", "volume", "block", "object storage"],
            "database": ["database", "autonomous", "db system"]
        }
        
        all_changes = additions + removals
        for change in all_changes:
            change_lower = change.lower()
            categorized = False
            for category, kw_list in keywords.items():
                if any(kw in change_lower for kw in kw_list):
                    categories[category] += 1
                    categorized = True
                    break
            if not categorized:
                categories["other"] += 1
        
        return {k: v for k, v in categories.items() if v > 0}
    
    def _summarize_changes(self, additions: int, removals: int) -> str:
        """Summarize detected changes."""
        if additions == 0 and removals == 0:
            return "No significant changes detected"
        elif additions > removals:
            return f"Net growth: {additions} additions, {removals} removals"
        elif removals > additions:
            return f"Net reduction: {removals} removals, {additions} additions"
        else:
            return f"Balanced changes: {additions} additions, {removals} removals"
    
    def _generate_change_recommendations(
        self,
        analysis: Optional[Dict]
    ) -> List[Dict]:
        """Generate recommendations based on changes."""
        if not analysis:
            return []
        
        recommendations = []
        change_types = analysis.get("change_types", {})
        
        if change_types.get("compute", 0) > 5:
            recommendations.append({
                "priority": "medium",
                "category": "compute_changes",
                "description": "Significant compute changes detected",
                "action": "Review compute changes for capacity and cost impact"
            })
        
        if change_types.get("networking", 0) > 3:
            recommendations.append({
                "priority": "high",
                "category": "network_changes",
                "description": "Network configuration changes detected",
                "action": "Verify security rules and connectivity"
            })
        
        if analysis.get("removals", 0) > 10:
            recommendations.append({
                "priority": "high",
                "category": "resource_removal",
                "description": "Many resources removed",
                "action": "Verify intentional cleanup vs accidental deletion"
            })
        
        return recommendations
    
    def generate_audit_report(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive infrastructure audit report.
        
        Args:
            compartment_id: Optional compartment scope
            region: Optional region scope
            
        Returns:
            Full audit report with all analyses
        """
        try:
            # Run all analyses
            discovery = self.run_full_discovery(compartment_id, region)
            capacity = self.generate_capacity_report(compartment_id, region)
            changes = self.detect_changes()
            
            # Aggregate findings
            all_recommendations = []
            
            if "recommendations" in discovery:
                all_recommendations.extend(discovery["recommendations"])
            if "capacity_recommendations" in capacity:
                all_recommendations.extend(capacity["capacity_recommendations"])
            if "recommendations" in changes:
                all_recommendations.extend(changes["recommendations"])
            
            # Prioritize
            prioritized = sorted(
                all_recommendations,
                key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.get("priority"), 4)
            )
            
            return {
                "report_type": "infrastructure_audit",
                "generated_at": datetime.now().isoformat(),
                "scope": {
                    "compartment_id": compartment_id,
                    "region": region
                },
                "executive_summary": self._generate_audit_summary(discovery, capacity, changes),
                "discovery_results": discovery,
                "capacity_analysis": capacity,
                "change_detection": changes,
                "prioritized_recommendations": prioritized[:15],
                "compliance_status": discovery.get("tagging_compliance", {}),
                "health_status": discovery.get("health_assessment", {})
            }
            
        except Exception as e:
            logger.error(f"Error generating audit report: {e}")
            return {"error": str(e)}
    
    def _generate_audit_summary(
        self,
        discovery: Dict,
        capacity: Dict,
        changes: Dict
    ) -> str:
        """Generate executive summary for audit."""
        parts = []
        
        # Resource summary
        total = discovery.get("total_resources", 0)
        parts.append(f"Infrastructure audit complete: {total} resources discovered")
        
        # Health status
        health = discovery.get("health_assessment", {})
        health_status = health.get("status", "unknown")
        parts.append(f"Health status: {health_status}")
        
        # Capacity assessment
        assessment = capacity.get("overall_assessment", {})
        if assessment.get("status"):
            parts.append(f"Capacity score: {assessment.get('overall_score', 0)}% ({assessment.get('status')})")
        
        # Change status
        if changes.get("changes_detected"):
            change_count = changes.get("change_analysis", {}).get("total_changes", 0)
            parts.append(f"{change_count} infrastructure changes detected")
        
        return ". ".join(parts)
