"""
Cost Analysis Skill for MCP-OCI

Provides high-level cost analysis, trend detection, optimization recommendations,
and anomaly detection following the skillz pattern.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .adapters import CostClientAdapter

logger = logging.getLogger(__name__)


@dataclass
class CostTrend:
    """Represents a cost trend analysis result."""
    direction: str  # "increasing", "decreasing", "stable"
    change_percent: float
    period: str
    forecast: Optional[float] = None
    confidence: float = 0.0


@dataclass
class CostAnomaly:
    """Represents a detected cost anomaly."""
    date: str
    service: str
    compartment: str
    expected_cost: float
    actual_cost: float
    deviation_percent: float
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class OptimizationRecommendation:
    """Represents a cost optimization recommendation."""
    category: str
    priority: str  # "low", "medium", "high"
    description: str
    estimated_savings: float
    implementation_effort: str  # "low", "medium", "high"
    affected_resources: List[str] = field(default_factory=list)


class CostAnalysisSkill:
    """
    Cost Analysis Skill - Orchestrates cost tools for comprehensive analysis.
    
    Capabilities:
    - Cost trend analysis with forecasting
    - Anomaly detection and alerting
    - Service and compartment cost breakdown
    - Optimization recommendations
    - Budget tracking and variance analysis
    """
    
    SKILL_NAME = "cost-analysis"
    SKILL_VERSION = "1.0.0"
    
    def __init__(self, client: Optional[CostClientAdapter] = None):
        """
        Initialize the Cost Analysis Skill.
        
        Args:
            client: Optional pre-configured CostClientAdapter
        """
        self.client = client or CostClientAdapter()
    
    def analyze_cost_trend(
        self,
        tenancy_ocid: str,
        months_back: int = 6,
        budget_ocid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze cost trends over time with forecasting.
        
        Args:
            tenancy_ocid: OCI tenancy OCID
            months_back: Number of months to analyze
            budget_ocid: Optional budget OCID for variance calculation
            
        Returns:
            Cost trend analysis including direction, forecast, and budget variance
        """
        try:
            # Get monthly trend with forecast
            trend_data = self.client.monthly_trend_forecast(
                tenancy_ocid=tenancy_ocid,
                months_back=months_back,
                budget_ocid=budget_ocid
            )
            
            if "error" in trend_data:
                return trend_data
            
            # Extract data from response
            data = trend_data.get("data", trend_data)
            series = data.get("series", [])
            forecast = data.get("forecast", {})
            budget = data.get("budget", {})
            
            # Calculate trend direction
            trend = self._calculate_trend_direction(series)
            
            # Generate recommendations based on trend
            recommendations = self._generate_trend_recommendations(
                trend, series, forecast, budget
            )
            
            return {
                "analysis_type": "cost_trend",
                "period": {
                    "months_analyzed": months_back,
                    "series_count": len(series)
                },
                "trend": {
                    "direction": trend.direction,
                    "change_percent": trend.change_percent,
                    "confidence": trend.confidence
                },
                "forecast": {
                    "next_month": forecast.get("next_month"),
                    "currency": forecast.get("currency")
                } if forecast else None,
                "budget_variance": budget if budget else None,
                "monthly_series": series,
                "recommendations": recommendations,
                "summary": self._generate_trend_summary(trend, forecast)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cost trend: {e}")
            return {"error": str(e)}
    
    def _calculate_trend_direction(self, series: List[Dict]) -> CostTrend:
        """Calculate the direction of cost trend from series data."""
        if not series or len(series) < 2:
            return CostTrend(
                direction="stable",
                change_percent=0.0,
                period="insufficient_data",
                confidence=0.0
            )
        
        # Get first and last months with data
        costs = [s.get("actual", 0) for s in series if s.get("actual", 0) > 0]
        
        if len(costs) < 2:
            return CostTrend(
                direction="stable",
                change_percent=0.0,
                period=f"{len(series)} months",
                confidence=0.5
            )
        
        first_cost = costs[0]
        last_cost = costs[-1]
        
        if first_cost == 0:
            change_percent = 100.0 if last_cost > 0 else 0.0
        else:
            change_percent = ((last_cost - first_cost) / first_cost) * 100
        
        # Determine direction based on change threshold
        if change_percent > 10:
            direction = "increasing"
        elif change_percent < -10:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Calculate confidence based on data consistency
        if len(costs) >= 6:
            confidence = 0.9
        elif len(costs) >= 3:
            confidence = 0.7
        else:
            confidence = 0.5
        
        return CostTrend(
            direction=direction,
            change_percent=round(change_percent, 2),
            period=f"{len(series)} months",
            confidence=confidence
        )
    
    def _generate_trend_recommendations(
        self,
        trend: CostTrend,
        series: List[Dict],
        forecast: Optional[Dict],
        budget: Optional[Dict]
    ) -> List[Dict]:
        """Generate recommendations based on trend analysis."""
        recommendations = []
        
        if trend.direction == "increasing" and trend.change_percent > 20:
            recommendations.append({
                "priority": "high",
                "category": "cost_control",
                "description": f"Costs increasing {trend.change_percent:.1f}% over {trend.period}. Review recent service additions and usage patterns.",
                "action": "Run service_cost_drilldown to identify top contributors"
            })
        
        if forecast and forecast.get("next_month"):
            forecast_amt = forecast.get("next_month", 0)
            if series and len(series) > 0:
                recent_avg = sum(s.get("actual", 0) for s in series[-3:]) / 3
                if forecast_amt > recent_avg * 1.2:
                    recommendations.append({
                        "priority": "medium",
                        "category": "forecast_warning",
                        "description": f"Forecast ({forecast_amt:.2f}) exceeds recent 3-month average by >20%",
                        "action": "Review upcoming projects and resource provisioning"
                    })
        
        if budget:
            if budget.get("status") == "OVER":
                recommendations.append({
                    "priority": "critical",
                    "category": "budget_alert",
                    "description": "Forecast exceeds committed budget credits by >5%",
                    "action": "Immediate cost optimization review required"
                })
            elif budget.get("status") == "UNDER":
                recommendations.append({
                    "priority": "low",
                    "category": "budget_info",
                    "description": "Under-consuming budget credits by >15%",
                    "action": "Consider accelerating projects or redistributing credits"
                })
        
        return recommendations
    
    def _generate_trend_summary(self, trend: CostTrend, forecast: Optional[Dict]) -> str:
        """Generate a human-readable trend summary."""
        summary = f"Costs are {trend.direction}"
        
        if trend.direction != "stable":
            summary += f" ({abs(trend.change_percent):.1f}% {'increase' if trend.direction == 'increasing' else 'decrease'} over {trend.period})"
        
        if forecast and forecast.get("next_month"):
            summary += f". Next month forecast: {forecast.get('currency', 'USD')} {forecast.get('next_month'):.2f}"
        
        return summary
    
    def detect_anomalies(
        self,
        tenancy_ocid: str,
        time_start: str,
        time_end: str,
        threshold: float = 2.0,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Detect cost anomalies and spikes.
        
        Args:
            tenancy_ocid: OCI tenancy OCID
            time_start: Start date (YYYY-MM-DD)
            time_end: End date (YYYY-MM-DD)
            threshold: Z-score threshold for anomaly detection
            top_n: Number of top anomalies to return
            
        Returns:
            Detected anomalies with explanations
        """
        try:
            # Get cost spikes with explanations
            spikes_data = self.client.top_cost_spikes_explain(
                tenancy_ocid=tenancy_ocid,
                time_start=time_start,
                time_end=time_end,
                top_n=top_n
            )
            
            if "error" in spikes_data:
                return spikes_data
            
            data = spikes_data.get("data", spikes_data)
            spikes = data.get("spikes", [])
            
            # Classify anomalies by severity
            anomalies = []
            for spike in spikes:
                severity = self._classify_anomaly_severity(spike)
                anomalies.append({
                    "date": spike.get("date"),
                    "delta": spike.get("delta"),
                    "severity": severity,
                    "top_services": spike.get("services", [])[:5],
                    "top_compartments": spike.get("compartments", [])[:5],
                    "explanation": self._generate_anomaly_explanation(spike, severity)
                })
            
            return {
                "analysis_type": "anomaly_detection",
                "period": {"start": time_start, "end": time_end},
                "threshold": threshold,
                "total_anomalies": len(anomalies),
                "anomalies": anomalies,
                "severity_breakdown": self._count_by_severity(anomalies),
                "recommendations": self._generate_anomaly_recommendations(anomalies)
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {"error": str(e)}
    
    def _classify_anomaly_severity(self, spike: Dict) -> str:
        """Classify anomaly severity based on cost delta."""
        delta = spike.get("delta", 0)
        
        if delta > 10000:
            return "critical"
        elif delta > 1000:
            return "high"
        elif delta > 100:
            return "medium"
        else:
            return "low"
    
    def _generate_anomaly_explanation(self, spike: Dict, severity: str) -> str:
        """Generate explanation for anomaly."""
        date = spike.get("date", "unknown")
        delta = spike.get("delta", 0)
        services = spike.get("services", [])
        
        explanation = f"Cost spike of ${delta:.2f} detected on {date}"
        
        if services:
            top_service = services[0]
            explanation += f". Primary contributor: {top_service.get('service', 'Unknown')} (${top_service.get('cost', 0):.2f})"
        
        return explanation
    
    def _count_by_severity(self, anomalies: List[Dict]) -> Dict[str, int]:
        """Count anomalies by severity level."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            counts[severity] = counts.get(severity, 0) + 1
        return counts
    
    def _generate_anomaly_recommendations(self, anomalies: List[Dict]) -> List[Dict]:
        """Generate recommendations based on detected anomalies."""
        recommendations = []
        
        severity_counts = self._count_by_severity(anomalies)
        
        if severity_counts.get("critical", 0) > 0:
            recommendations.append({
                "priority": "critical",
                "category": "immediate_action",
                "description": f"{severity_counts['critical']} critical cost spikes detected",
                "action": "Review critical anomalies immediately and identify root cause"
            })
        
        if severity_counts.get("high", 0) > 2:
            recommendations.append({
                "priority": "high",
                "category": "investigation",
                "description": "Multiple high-severity cost spikes detected",
                "action": "Investigate patterns in service usage and compartment spending"
            })
        
        # Aggregate service recommendations
        service_counts: Dict[str, int] = {}
        for anomaly in anomalies:
            for service in anomaly.get("top_services", []):
                svc_name = service.get("service", "Unknown")
                service_counts[svc_name] = service_counts.get(svc_name, 0) + 1
        
        repeat_services = [s for s, c in service_counts.items() if c > 1]
        if repeat_services:
            recommendations.append({
                "priority": "medium",
                "category": "service_review",
                "description": f"Services appearing in multiple spikes: {', '.join(repeat_services[:3])}",
                "action": "Review resource provisioning and auto-scaling for these services"
            })
        
        return recommendations
    
    def get_service_breakdown(
        self,
        tenancy_ocid: str,
        time_start: str,
        time_end: str,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Get detailed service cost breakdown.
        
        Args:
            tenancy_ocid: OCI tenancy OCID
            time_start: Start date (YYYY-MM-DD)
            time_end: End date (YYYY-MM-DD)
            top_n: Number of top services to return
            
        Returns:
            Service breakdown with compartment details
        """
        try:
            drilldown = self.client.service_cost_drilldown(
                tenancy_ocid=tenancy_ocid,
                time_start=time_start,
                time_end=time_end,
                top_n=top_n
            )
            
            if "error" in drilldown:
                return drilldown
            
            data = drilldown.get("data", drilldown)
            services = data.get("top", [])
            
            # Calculate percentage breakdown
            total_cost = sum(s.get("total", 0) for s in services)
            
            service_analysis = []
            for service in services:
                svc_cost = service.get("total", 0)
                percentage = (svc_cost / total_cost * 100) if total_cost > 0 else 0
                
                service_analysis.append({
                    "service": service.get("service"),
                    "total_cost": svc_cost,
                    "percentage": round(percentage, 2),
                    "top_compartments": service.get("compartments", [])[:5],
                    "optimization_potential": self._assess_optimization_potential(service)
                })
            
            return {
                "analysis_type": "service_breakdown",
                "period": {"start": time_start, "end": time_end},
                "total_cost": total_cost,
                "service_count": len(services),
                "services": service_analysis,
                "concentration_analysis": self._analyze_cost_concentration(service_analysis),
                "recommendations": self._generate_service_recommendations(service_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error getting service breakdown: {e}")
            return {"error": str(e)}
    
    def _assess_optimization_potential(self, service: Dict) -> str:
        """Assess optimization potential for a service."""
        service_name = service.get("service", "").lower()
        
        # High optimization potential services
        high_potential = ["compute", "block storage", "object storage", "database"]
        if any(hp in service_name for hp in high_potential):
            return "high"
        
        # Medium potential
        medium_potential = ["networking", "load balancer", "functions"]
        if any(mp in service_name for mp in medium_potential):
            return "medium"
        
        return "low"
    
    def _analyze_cost_concentration(self, services: List[Dict]) -> Dict[str, Any]:
        """Analyze cost concentration across services."""
        if not services:
            return {"concentration": "none", "top_3_percentage": 0}
        
        # Calculate concentration
        percentages = [s.get("percentage", 0) for s in services]
        top_3_pct = sum(percentages[:3])
        
        if top_3_pct > 80:
            concentration = "high"
            risk = "Consider diversifying workloads to reduce single-service risk"
        elif top_3_pct > 60:
            concentration = "medium"
            risk = "Acceptable concentration but monitor for changes"
        else:
            concentration = "low"
            risk = "Well-distributed costs across services"
        
        return {
            "concentration": concentration,
            "top_3_percentage": round(top_3_pct, 2),
            "assessment": risk
        }
    
    def _generate_service_recommendations(self, services: List[Dict]) -> List[Dict]:
        """Generate recommendations based on service breakdown."""
        recommendations = []
        
        for service in services[:5]:  # Focus on top 5
            if service.get("optimization_potential") == "high":
                svc_name = service.get("service", "Unknown")
                recommendations.append({
                    "priority": "medium",
                    "category": "optimization",
                    "service": svc_name,
                    "description": f"{svc_name} has high optimization potential",
                    "actions": self._get_service_optimization_actions(svc_name)
                })
        
        return recommendations
    
    def _get_service_optimization_actions(self, service_name: str) -> List[str]:
        """Get specific optimization actions for a service."""
        service_lower = service_name.lower()
        
        actions = {
            "compute": [
                "Review instance shapes and right-size",
                "Consider preemptible instances for batch workloads",
                "Evaluate reserved capacity commitments"
            ],
            "block storage": [
                "Review volume performance tiers",
                "Delete unattached volumes",
                "Consider lower-cost storage tiers"
            ],
            "object storage": [
                "Enable lifecycle policies for archival",
                "Review storage tier placement",
                "Clean up temporary data"
            ],
            "database": [
                "Evaluate Autonomous vs VM/BM options",
                "Review backup retention policies",
                "Consider scaling down non-production"
            ]
        }
        
        for key, action_list in actions.items():
            if key in service_lower:
                return action_list
        
        return ["Review usage patterns", "Consider reserved capacity"]
    
    def generate_optimization_report(
        self,
        tenancy_ocid: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive cost optimization report.
        
        Args:
            tenancy_ocid: OCI tenancy OCID
            days_back: Number of days to analyze
            
        Returns:
            Comprehensive optimization report with actionable recommendations
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            time_start = start_date.strftime("%Y-%m-%d")
            time_end = end_date.strftime("%Y-%m-%d")
            
            # Gather all analyses
            trend = self.analyze_cost_trend(tenancy_ocid, months_back=6)
            anomalies = self.detect_anomalies(tenancy_ocid, time_start, time_end)
            breakdown = self.get_service_breakdown(tenancy_ocid, time_start, time_end)
            
            # Aggregate recommendations
            all_recommendations = []
            
            if "recommendations" in trend:
                all_recommendations.extend(trend["recommendations"])
            if "recommendations" in anomalies:
                all_recommendations.extend(anomalies["recommendations"])
            if "recommendations" in breakdown:
                all_recommendations.extend(breakdown["recommendations"])
            
            # Prioritize recommendations
            prioritized = sorted(
                all_recommendations,
                key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.get("priority"), 4)
            )
            
            return {
                "report_type": "cost_optimization",
                "generated_at": datetime.now().isoformat(),
                "period": {"start": time_start, "end": time_end},
                "executive_summary": self._generate_executive_summary(trend, anomalies, breakdown),
                "trend_analysis": trend,
                "anomaly_analysis": anomalies,
                "service_breakdown": breakdown,
                "prioritized_recommendations": prioritized[:10],
                "estimated_savings_potential": self._estimate_total_savings(breakdown)
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization report: {e}")
            return {"error": str(e)}
    
    def _generate_executive_summary(
        self,
        trend: Dict,
        anomalies: Dict,
        breakdown: Dict
    ) -> str:
        """Generate executive summary from analyses."""
        parts = []
        
        # Trend summary
        if trend.get("summary"):
            parts.append(trend["summary"])
        
        # Anomaly summary
        if anomalies.get("total_anomalies", 0) > 0:
            severity = anomalies.get("severity_breakdown", {})
            critical = severity.get("critical", 0)
            high = severity.get("high", 0)
            if critical or high:
                parts.append(f"{critical + high} significant cost anomalies detected")
        
        # Service concentration
        if breakdown.get("concentration_analysis"):
            conc = breakdown["concentration_analysis"]
            parts.append(f"Cost concentration: {conc.get('concentration', 'unknown')} (top 3 services: {conc.get('top_3_percentage', 0):.0f}%)")
        
        return ". ".join(parts) if parts else "Analysis complete."
    
    def _estimate_total_savings(self, breakdown: Dict) -> Dict[str, Any]:
        """Estimate total potential savings from breakdown analysis."""
        total_cost = breakdown.get("total_cost", 0)
        high_potential = sum(
            s.get("total_cost", 0)
            for s in breakdown.get("services", [])
            if s.get("optimization_potential") == "high"
        )
        
        # Conservative estimate: 10-20% savings on high-potential services
        estimated_min = high_potential * 0.10
        estimated_max = high_potential * 0.20
        
        return {
            "high_potential_spend": high_potential,
            "estimated_savings_range": {
                "min": round(estimated_min, 2),
                "max": round(estimated_max, 2)
            },
            "percentage_of_total": round((high_potential / total_cost * 100) if total_cost > 0 else 0, 2)
        }
