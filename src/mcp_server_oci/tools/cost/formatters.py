"""
Cost domain-specific formatters.
"""
from __future__ import annotations

import json
from typing import Any

from mcp_server_oci.core.formatters import Formatter


class CostFormatter:
    """Cost-specific formatting utilities."""
    
    @staticmethod
    def to_json(data: Any) -> str:
        """Format as JSON."""
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def summary_markdown(data: dict) -> str:
        """Format cost summary as markdown."""
        lines = ["# Cost Summary\n"]
        
        # Summary section
        lines.append(f"**Total Cost:** {Formatter.format_currency(data.get('total_cost', 0))}")
        lines.append(f"**Period:** {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}")
        lines.append(f"**Daily Average:** {Formatter.format_currency(data.get('daily_average', 0))}")
        
        if data.get('month_over_month_change') is not None:
            change = data['month_over_month_change']
            indicator = Formatter.trend_indicator(change)
            lines.append(f"**Month-over-Month:** {indicator}")
        
        lines.append("")
        
        # Service breakdown
        if data.get('by_service'):
            lines.append("## Cost by Service\n")
            lines.append("| Service | Cost | % of Total |")
            lines.append("|---------|------|------------|")
            for svc in data['by_service'][:10]:
                cost = Formatter.format_currency(svc.get('cost', 0))
                pct = f"{svc.get('percentage', 0):.1f}%"
                lines.append(f"| {svc.get('service', 'Unknown')} | {cost} | {pct} |")
            lines.append("")
        
        # Compartment breakdown
        if data.get('by_compartment'):
            lines.append("## Cost by Compartment\n")
            lines.append("| Compartment | Cost | % of Total |")
            lines.append("|-------------|------|------------|")
            for comp in data['by_compartment'][:10]:
                cost = Formatter.format_currency(comp.get('cost', 0))
                pct = f"{comp.get('percentage', 0):.1f}%"
                name = comp.get('compartment_name', 'Unknown')
                lines.append(f"| {name} | {cost} | {pct} |")
            lines.append("")
        
        # Forecast
        if data.get('forecast'):
            forecast = data['forecast']
            lines.append("## Forecast\n")
            lines.append(f"**Next Period Estimate:** {Formatter.format_currency(forecast.get('estimate', 0))}")
            if forecast.get('confidence'):
                lines.append(f"**Confidence:** {forecast['confidence']}%")
        
        return "\n".join(lines)
    
    @staticmethod
    def compartment_markdown(data: dict) -> str:
        """Format compartment cost breakdown as markdown."""
        lines = ["# Cost by Compartment\n"]
        
        lines.append(f"**Total:** {Formatter.format_currency(data.get('total_cost', 0))}")
        lines.append(f"**Period:** {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}")
        lines.append("")
        
        for comp in data.get('compartments', []):
            lines.append(f"## {comp.get('name', 'Unknown')}")
            lines.append(f"**Total:** {Formatter.format_currency(comp.get('cost', 0))}")
            
            if comp.get('services'):
                lines.append("\n| Service | Cost |")
                lines.append("|---------|------|")
                for svc in comp['services'][:5]:
                    cost = Formatter.format_currency(svc.get('cost', 0))
                    lines.append(f"| {svc.get('service', 'Unknown')} | {cost} |")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def service_drilldown_markdown(data: dict) -> str:
        """Format service drilldown as markdown."""
        lines = ["# Service Cost Drilldown\n"]
        
        lines.append(f"**Total Analyzed:** {Formatter.format_currency(data.get('total', 0))}")
        lines.append(f"**Period:** {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}")
        lines.append("")
        
        for i, svc in enumerate(data.get('services', []), 1):
            lines.append(f"## {i}. {svc.get('service', 'Unknown')}")
            cost = Formatter.format_currency(svc.get('cost', 0))
            pct = svc.get('percentage', 0)
            lines.append(f"**Cost:** {cost} ({pct:.1f}% of total)")
            
            if svc.get('top_compartments'):
                lines.append("\n**Top Compartments:**")
                for comp in svc['top_compartments'][:3]:
                    comp_cost = Formatter.format_currency(comp.get('cost', 0))
                    lines.append(f"- {comp.get('name', 'Unknown')}: {comp_cost}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def trend_markdown(data: dict) -> str:
        """Format trend analysis as markdown."""
        lines = ["# Monthly Cost Trend\n"]
        
        # Summary
        if data.get('summary'):
            summary = data['summary']
            lines.append(f"**Period:** Last {summary.get('months_analyzed', 0)} months")
            lines.append(f"**Total Spend:** {Formatter.format_currency(summary.get('total_spend', 0))}")
            lines.append(f"**Average Monthly:** {Formatter.format_currency(summary.get('average_monthly', 0))}")
            lines.append("")
        
        # Monthly breakdown table
        lines.append("## Monthly Breakdown\n")
        lines.append("| Month | Cost | Change |")
        lines.append("|-------|------|--------|")
        
        for item in data.get('monthly_costs', []):
            cost = Formatter.format_currency(item.get('cost', 0))
            change = item.get('change_percent')
            if change is not None:
                change_str = f"{change:+.1f}%"
            else:
                change_str = "—"
            lines.append(f"| {item.get('month', 'Unknown')} | {cost} | {change_str} |")
        
        lines.append("")
        
        # Forecast
        if data.get('forecast'):
            forecast = data['forecast']
            lines.append("## Forecast\n")
            lines.append(f"**Next Month Estimate:** {Formatter.format_currency(forecast.get('estimate', 0))}")
            trend = forecast.get('trend', 'stable')
            lines.append(f"**Trend:** {trend.capitalize()}")
        
        # Budget status
        if data.get('budget_variance'):
            bv = data['budget_variance']
            lines.append("\n## Budget Status\n")
            lines.append(f"**Budget:** {Formatter.format_currency(bv.get('budget_amount', 0))}")
            lines.append(f"**Actual:** {Formatter.format_currency(bv.get('actual_spend', 0))}")
            variance = bv.get('variance_percent', 0)
            status = "Under budget ✅" if variance < 0 else "Over budget ⚠️"
            lines.append(f"**Variance:** {variance:+.1f}% ({status})")
        
        return "\n".join(lines)
    
    @staticmethod
    def anomaly_markdown(data: dict) -> str:
        """Format anomaly detection results as markdown."""
        lines = ["# Cost Anomaly Detection\n"]
        
        # Summary
        summary = data.get('summary', {})
        lines.append(f"**Total Anomalies Found:** {summary.get('total_anomalies', 0)}")
        lines.append(f"- 🔴 Critical: {summary.get('critical', 0)}")
        lines.append(f"- 🟠 High: {summary.get('high', 0)}")
        lines.append(f"- 🟡 Medium: {summary.get('medium', 0)}")
        lines.append(f"- 🟢 Low: {summary.get('low', 0)}")
        lines.append("")
        
        # Detection parameters
        params = data.get('detection_params', {})
        lines.append(f"**Detection Threshold:** {params.get('threshold_std_dev', 2.0)} standard deviations")
        lines.append(f"**Period:** {params.get('period', 'N/A')}")
        lines.append("")
        
        # Individual anomalies
        if data.get('anomalies'):
            lines.append("## Detected Anomalies\n")
            
            severity_icons = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            
            for anomaly in data['anomalies']:
                severity = anomaly.get('severity', 'low')
                icon = severity_icons.get(severity, "⚪")
                
                lines.append(f"### {icon} {anomaly.get('date', 'Unknown Date')}")
                lines.append(f"**Severity:** {severity.upper()}")
                
                cost = Formatter.format_currency(anomaly.get('cost', 0))
                expected = Formatter.format_currency(anomaly.get('expected_cost', 0))
                deviation = anomaly.get('deviation_percent', 0)
                
                lines.append(f"**Cost:** {cost} (Expected: {expected})")
                lines.append(f"**Deviation:** +{deviation:.1f}% above average")
                
                if anomaly.get('root_cause'):
                    lines.append("\n**Root Cause Analysis:**")
                    contributors = anomaly['root_cause'].get('contributors', [])
                    for contrib in contributors[:3]:
                        increase = Formatter.format_currency(contrib.get('increase', 0))
                        lines.append(f"- {contrib.get('service', 'Unknown')}: +{increase}")
                
                lines.append("")
        else:
            lines.append("✅ No significant anomalies detected in the specified period.")
        
        return "\n".join(lines)
