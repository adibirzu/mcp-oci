"""
Compute Management Skill

High-level skill for managing OCI compute instances with intelligent operations.
Maps to compute server tools for agent-friendly operations.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ComputeManagementSkill:
    """
    Skill for managing OCI compute instances.
    
    Provides high-level operations:
    - Fleet health assessment
    - Instance lifecycle management
    - Resource optimization recommendations
    - Metrics analysis
    """
    
    def __init__(self, client=None):
        """Initialize with optional client adapter."""
        self.client = client
    
    def assess_fleet_health(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess overall compute fleet health.
        
        Returns:
            - total_instances: Total count
            - health_score: 0-100 score
            - state_distribution: Counts by lifecycle state
            - issues: List of identified issues
            - recommendations: Optimization recommendations
        """
        try:
            # Get all instances
            if self.client:
                instances = self.client.list_instances(compartment_id, region)
            else:
                return {"error": "No client configured"}
            
            if isinstance(instances, dict) and "error" in instances:
                return instances
            
            total = len(instances)
            if total == 0:
                return {
                    "analysis_type": "fleet_health",
                    "total_instances": 0,
                    "health_score": 100,
                    "state_distribution": {},
                    "issues": [],
                    "recommendations": ["No instances found - consider provisioning resources"]
                }
            
            # Calculate state distribution
            state_dist = {}
            running_count = 0
            stopped_count = 0
            terminating_count = 0
            
            for inst in instances:
                state = inst.get("lifecycle_state", "UNKNOWN")
                state_dist[state] = state_dist.get(state, 0) + 1
                if state == "RUNNING":
                    running_count += 1
                elif state == "STOPPED":
                    stopped_count += 1
                elif state in ("TERMINATING", "TERMINATED"):
                    terminating_count += 1
            
            # Calculate health score
            health_score = 100
            issues = []
            recommendations = []
            
            # Penalize stopped instances
            if stopped_count > 0:
                stopped_pct = (stopped_count / total) * 100
                if stopped_pct > 50:
                    health_score -= 30
                    issues.append({
                        "type": "high_stopped_instances",
                        "severity": "warning",
                        "count": stopped_count,
                        "percentage": round(stopped_pct, 1),
                        "message": f"{stopped_count} instances ({stopped_pct:.1f}%) are stopped"
                    })
                    recommendations.append(f"Review {stopped_count} stopped instances - consider terminating unused ones to save costs")
                elif stopped_pct > 20:
                    health_score -= 15
                    issues.append({
                        "type": "moderate_stopped_instances",
                        "severity": "info",
                        "count": stopped_count,
                        "message": f"{stopped_count} instances are stopped"
                    })
            
            # Check for terminating instances
            if terminating_count > 0:
                issues.append({
                    "type": "terminating_instances",
                    "severity": "info",
                    "count": terminating_count,
                    "message": f"{terminating_count} instances are being terminated"
                })
            
            # Check utilization rate
            if running_count > 0:
                utilization_rate = (running_count / total) * 100
                if utilization_rate < 50:
                    recommendations.append(f"Only {utilization_rate:.1f}% of instances are running - review provisioning strategy")
            
            return {
                "analysis_type": "fleet_health",
                "timestamp": datetime.utcnow().isoformat(),
                "total_instances": total,
                "health_score": max(0, health_score),
                "state_distribution": state_dist,
                "running_instances": running_count,
                "stopped_instances": stopped_count,
                "utilization_rate": round((running_count / total) * 100, 1) if total > 0 else 0,
                "issues": issues,
                "recommendations": recommendations,
                "summary": f"Fleet has {total} instances, {running_count} running, health score: {health_score}"
            }
            
        except Exception as e:
            logger.error(f"Error assessing fleet health: {e}")
            return {"error": str(e), "analysis_type": "fleet_health"}
    
    def analyze_instance_performance(
        self,
        instance_id: str,
        window: str = "1h"
    ) -> Dict[str, Any]:
        """
        Analyze performance metrics for an instance.
        
        Returns:
            - cpu_analysis: CPU utilization insights
            - performance_score: 0-100 score
            - recommendations: Performance optimization suggestions
        """
        try:
            if self.client:
                metrics = self.client.get_instance_metrics(instance_id, window)
            else:
                return {"error": "No client configured"}
            
            if isinstance(metrics, dict) and "error" in metrics:
                return {"error": metrics.get("error"), "analysis_type": "instance_performance"}
            
            cpu_metrics = metrics.get("cpu_metrics", {})
            instance_info = metrics.get("instance", {})
            
            avg_cpu = cpu_metrics.get("average", 0)
            max_cpu = cpu_metrics.get("max", 0)
            min_cpu = cpu_metrics.get("min", 0)
            
            # Calculate performance score
            score = 100
            recommendations = []
            insights = []
            
            # High CPU utilization
            if avg_cpu > 80:
                score -= 30
                insights.append({
                    "type": "high_cpu",
                    "severity": "critical",
                    "value": round(avg_cpu, 1),
                    "message": f"Average CPU at {avg_cpu:.1f}% - instance may be overloaded"
                })
                recommendations.append("Consider scaling up to a larger shape or adding more instances")
            elif avg_cpu > 60:
                score -= 10
                insights.append({
                    "type": "elevated_cpu",
                    "severity": "warning",
                    "value": round(avg_cpu, 1),
                    "message": f"CPU utilization at {avg_cpu:.1f}% - monitor closely"
                })
            
            # Low CPU utilization (wasteful)
            if avg_cpu < 10 and max_cpu < 20:
                score -= 15
                insights.append({
                    "type": "underutilized",
                    "severity": "info",
                    "value": round(avg_cpu, 1),
                    "message": f"Instance appears underutilized (avg: {avg_cpu:.1f}%)"
                })
                recommendations.append("Consider downsizing to a smaller shape to reduce costs")
            
            # CPU spikes
            if max_cpu > 90 and avg_cpu < 50:
                insights.append({
                    "type": "cpu_spikes",
                    "severity": "warning",
                    "value": round(max_cpu, 1),
                    "message": f"CPU spikes detected (max: {max_cpu:.1f}%, avg: {avg_cpu:.1f}%)"
                })
                recommendations.append("Investigate workload patterns - consider burstable shapes")
            
            return {
                "analysis_type": "instance_performance",
                "timestamp": datetime.utcnow().isoformat(),
                "instance_id": instance_id,
                "instance_name": instance_info.get("display_name"),
                "window": window,
                "cpu_analysis": {
                    "average": round(avg_cpu, 2),
                    "max": round(max_cpu, 2),
                    "min": round(min_cpu, 2),
                    "datapoints": cpu_metrics.get("datapoints_count", 0)
                },
                "performance_score": max(0, score),
                "insights": insights,
                "recommendations": recommendations,
                "summary": f"Instance CPU avg: {avg_cpu:.1f}%, performance score: {score}"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing instance performance: {e}")
            return {"error": str(e), "analysis_type": "instance_performance"}
    
    def recommend_rightsizing(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze instances and recommend rightsizing opportunities.
        
        Returns:
            - candidates: Instances that could be resized
            - potential_savings: Estimated cost reduction
            - recommendations: Specific resizing suggestions
        """
        try:
            if self.client:
                instances = self.client.list_instances(compartment_id, region)
            else:
                return {"error": "No client configured"}
            
            if isinstance(instances, dict) and "error" in instances:
                return instances
            
            candidates = []
            total_savings_potential = 0
            
            running_instances = [i for i in instances if i.get("lifecycle_state") == "RUNNING"]
            
            for inst in running_instances:
                shape = inst.get("shape", "")
                
                # Basic rightsizing heuristics (would need real metrics for accurate analysis)
                recommendation = None
                
                # Large shapes that might be oversized
                if "Standard2.8" in shape or "Standard2.16" in shape:
                    recommendation = {
                        "instance_id": inst.get("id"),
                        "instance_name": inst.get("display_name"),
                        "current_shape": shape,
                        "suggested_action": "Review for downsizing",
                        "reason": "Large shape - verify utilization justifies size",
                        "potential_monthly_savings_usd": 150 if "16" in shape else 75
                    }
                    total_savings_potential += recommendation["potential_monthly_savings_usd"]
                
                # Flex shapes without optimization
                elif "Flex" in shape:
                    recommendation = {
                        "instance_id": inst.get("id"),
                        "instance_name": inst.get("display_name"),
                        "current_shape": shape,
                        "suggested_action": "Verify OCPU/memory allocation",
                        "reason": "Flex shape - ensure resources match actual workload",
                        "potential_monthly_savings_usd": 50
                    }
                    total_savings_potential += 50
                
                if recommendation:
                    candidates.append(recommendation)
            
            return {
                "analysis_type": "rightsizing_recommendations",
                "timestamp": datetime.utcnow().isoformat(),
                "total_instances_analyzed": len(running_instances),
                "candidates_count": len(candidates),
                "candidates": candidates[:10],  # Top 10
                "potential_monthly_savings_usd": total_savings_potential,
                "summary": f"Found {len(candidates)} rightsizing opportunities with potential savings of ${total_savings_potential}/month"
            }
            
        except Exception as e:
            logger.error(f"Error generating rightsizing recommendations: {e}")
            return {"error": str(e), "analysis_type": "rightsizing_recommendations"}
    
    def generate_fleet_report(
        self,
        compartment_id: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive fleet management report.
        
        Combines health assessment, rightsizing, and inventory into one report.
        """
        try:
            health = self.assess_fleet_health(compartment_id, region)
            rightsizing = self.recommend_rightsizing(compartment_id, region)
            
            return {
                "report_type": "compute_fleet_report",
                "timestamp": datetime.utcnow().isoformat(),
                "health_assessment": health,
                "rightsizing_analysis": rightsizing,
                "executive_summary": {
                    "total_instances": health.get("total_instances", 0),
                    "health_score": health.get("health_score", 0),
                    "running_count": health.get("running_instances", 0),
                    "optimization_opportunities": rightsizing.get("candidates_count", 0),
                    "potential_savings": rightsizing.get("potential_monthly_savings_usd", 0)
                },
                "summary": f"Fleet report: {health.get('total_instances', 0)} instances, health score {health.get('health_score', 0)}, ${rightsizing.get('potential_monthly_savings_usd', 0)} savings potential"
            }
            
        except Exception as e:
            logger.error(f"Error generating fleet report: {e}")
            return {"error": str(e), "report_type": "compute_fleet_report"}


# =============================================================================
# Skill Tool Functions (for MCP registration)
# =============================================================================

def skill_assess_compute_fleet_health(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess compute fleet health with scoring and recommendations.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Fleet health assessment with score, state distribution, issues, and recommendations
    """
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.assess_fleet_health(compartment_id, region)


def skill_analyze_instance_performance(
    instance_id: str,
    window: str = "1h"
) -> Dict[str, Any]:
    """
    Analyze instance performance metrics with insights.
    
    Args:
        instance_id: Instance OCID to analyze
        window: Time window (1h or 24h)
    
    Returns:
        Performance analysis with CPU insights, score, and recommendations
    """
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.analyze_instance_performance(instance_id, window)


def skill_recommend_compute_rightsizing(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get rightsizing recommendations for compute instances.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Rightsizing candidates with potential savings estimates
    """
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.recommend_rightsizing(compartment_id, region)


def skill_generate_compute_fleet_report(
    compartment_id: Optional[str] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive compute fleet management report.
    
    Args:
        compartment_id: Optional compartment filter
        region: Optional region filter
    
    Returns:
        Complete report combining health, rightsizing, and executive summary
    """
    from .adapters import get_compute_client_adapter
    skill = ComputeManagementSkill(client=get_compute_client_adapter())
    return skill.generate_fleet_report(compartment_id, region)
