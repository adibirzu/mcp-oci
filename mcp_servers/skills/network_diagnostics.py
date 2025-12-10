"""
Network Diagnostics Skill for MCP-OCI

Provides network topology analysis, security assessment, connectivity diagnostics,
and troubleshooting capabilities following the skillz pattern.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .adapters import NetworkClientAdapter

logger = logging.getLogger(__name__)


@dataclass
class NetworkIssue:
    """Represents a network issue or finding."""
    severity: str  # "info", "warning", "critical"
    category: str  # "connectivity", "security", "configuration"
    description: str
    affected_resource: str
    recommendation: str


@dataclass
class SecurityFinding:
    """Represents a security finding in network configuration."""
    severity: str  # "low", "medium", "high", "critical"
    finding_type: str
    description: str
    vcn_id: str
    remediation: str


@dataclass
class TopologyNode:
    """Represents a node in network topology."""
    resource_type: str
    resource_id: str
    display_name: str
    connections: List[str] = field(default_factory=list)


class NetworkDiagnosticsSkill:
    """
    Network Diagnostics Skill - Orchestrates network tools for analysis and troubleshooting.
    
    Capabilities:
    - Network topology mapping
    - Public endpoint security analysis
    - Subnet utilization assessment
    - Connectivity validation
    - Security rule audit
    """
    
    SKILL_NAME = "network-diagnostics"
    SKILL_VERSION = "1.0.0"
    
    def __init__(self, client: Optional[NetworkClientAdapter] = None):
        """
        Initialize the Network Diagnostics Skill.
        
        Args:
            client: Optional pre-configured NetworkClientAdapter
        """
        self.client = client or NetworkClientAdapter()
    
    def analyze_topology(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze network topology for a compartment.
        
        Args:
            compartment_id: Optional compartment to analyze
            
        Returns:
            Network topology analysis including VCNs, subnets, and relationships
        """
        try:
            # Get VCNs
            vcns = self.client.list_vcns(compartment_id=compartment_id)
            
            if isinstance(vcns, dict) and "error" in vcns:
                return vcns
            
            # Build topology
            topology = {
                "vcns": [],
                "total_vcns": len(vcns),
                "total_subnets": 0,
                "subnet_distribution": {},
                "cidr_analysis": []
            }
            
            # Analyze each VCN
            for vcn in vcns:
                vcn_id = vcn.get("id")
                vcn_name = vcn.get("display_name", "Unknown")
                vcn_cidr = vcn.get("cidr_block", "")
                
                # Get subnets for this VCN
                subnets = self.client.list_subnets(
                    vcn_id=vcn_id,
                    compartment_id=compartment_id
                )
                
                subnet_count = len(subnets) if isinstance(subnets, list) else 0
                topology["total_subnets"] += subnet_count
                
                # Analyze subnets
                public_subnets = []
                private_subnets = []
                
                for subnet in (subnets if isinstance(subnets, list) else []):
                    subnet_info = {
                        "id": subnet.get("id"),
                        "display_name": subnet.get("display_name"),
                        "cidr_block": subnet.get("cidr_block"),
                        "is_public": not subnet.get("prohibit_public_ip_on_vnic", True)
                    }
                    
                    if subnet_info["is_public"]:
                        public_subnets.append(subnet_info)
                    else:
                        private_subnets.append(subnet_info)
                
                vcn_analysis = {
                    "id": vcn_id,
                    "display_name": vcn_name,
                    "cidr_block": vcn_cidr,
                    "subnet_count": subnet_count,
                    "public_subnets": len(public_subnets),
                    "private_subnets": len(private_subnets),
                    "subnets": {
                        "public": public_subnets,
                        "private": private_subnets
                    }
                }
                
                topology["vcns"].append(vcn_analysis)
                
                # CIDR analysis
                topology["cidr_analysis"].append({
                    "vcn": vcn_name,
                    "cidr": vcn_cidr,
                    "size": self._calculate_cidr_size(vcn_cidr)
                })
            
            # Generate insights
            topology["insights"] = self._generate_topology_insights(topology)
            topology["recommendations"] = self._generate_topology_recommendations(topology)
            
            return {
                "analysis_type": "network_topology",
                "timestamp": datetime.now().isoformat(),
                "scope": {"compartment_id": compartment_id},
                "topology": topology,
                "summary": self._generate_topology_summary(topology)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing topology: {e}")
            return {"error": str(e)}
    
    def _calculate_cidr_size(self, cidr: str) -> Dict[str, Any]:
        """Calculate CIDR block size and available IPs."""
        try:
            if "/" not in cidr:
                return {"prefix": 0, "total_ips": 0, "usable_ips": 0}
            
            prefix = int(cidr.split("/")[1])
            total_ips = 2 ** (32 - prefix)
            # OCI reserves 5 IPs per subnet
            usable_ips = total_ips - 5 if total_ips > 5 else 0
            
            return {
                "prefix": prefix,
                "total_ips": total_ips,
                "usable_ips": usable_ips
            }
        except Exception:
            return {"prefix": 0, "total_ips": 0, "usable_ips": 0}
    
    def _generate_topology_insights(self, topology: Dict) -> List[Dict]:
        """Generate insights from topology analysis."""
        insights = []
        
        # VCN count insight
        vcn_count = topology.get("total_vcns", 0)
        if vcn_count == 0:
            insights.append({
                "type": "info",
                "category": "infrastructure",
                "message": "No VCNs found in this compartment"
            })
        elif vcn_count > 10:
            insights.append({
                "type": "info",
                "category": "complexity",
                "message": f"{vcn_count} VCNs detected - consider using Hub-Spoke topology"
            })
        
        # Public subnet exposure
        total_public = sum(vcn.get("public_subnets", 0) for vcn in topology.get("vcns", []))
        total_private = sum(vcn.get("private_subnets", 0) for vcn in topology.get("vcns", []))
        
        if total_public > total_private:
            insights.append({
                "type": "warning",
                "category": "security",
                "message": f"More public ({total_public}) than private ({total_private}) subnets - review exposure requirements"
            })
        
        # Empty VCNs
        empty_vcns = [vcn for vcn in topology.get("vcns", []) if vcn.get("subnet_count", 0) == 0]
        if empty_vcns:
            insights.append({
                "type": "info",
                "category": "cleanup",
                "message": f"{len(empty_vcns)} VCN(s) have no subnets - consider cleanup"
            })
        
        return insights
    
    def _generate_topology_recommendations(self, topology: Dict) -> List[Dict]:
        """Generate recommendations from topology analysis."""
        recommendations = []
        
        # Check for public subnet exposure
        for vcn in topology.get("vcns", []):
            if vcn.get("public_subnets", 0) > 0 and vcn.get("private_subnets", 0) == 0:
                recommendations.append({
                    "priority": "high",
                    "category": "security",
                    "vcn": vcn.get("display_name"),
                    "description": "VCN has only public subnets",
                    "action": "Consider adding private subnets for backend services"
                })
        
        # Check subnet distribution
        for vcn in topology.get("vcns", []):
            if vcn.get("subnet_count", 0) == 1:
                recommendations.append({
                    "priority": "medium",
                    "category": "design",
                    "vcn": vcn.get("display_name"),
                    "description": "VCN has only one subnet",
                    "action": "Consider adding subnets for network segmentation"
                })
        
        return recommendations
    
    def _generate_topology_summary(self, topology: Dict) -> str:
        """Generate topology summary text."""
        vcn_count = topology.get("total_vcns", 0)
        subnet_count = topology.get("total_subnets", 0)
        
        total_public = sum(vcn.get("public_subnets", 0) for vcn in topology.get("vcns", []))
        total_private = sum(vcn.get("private_subnets", 0) for vcn in topology.get("vcns", []))
        
        return f"Network topology: {vcn_count} VCNs, {subnet_count} subnets ({total_public} public, {total_private} private)"
    
    def assess_security(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess network security posture.
        
        Args:
            compartment_id: Optional compartment to assess
            
        Returns:
            Security assessment with findings and recommendations
        """
        try:
            # Get public endpoints summary
            public_endpoints = self.client.summarize_public_endpoints(
                compartment_id=compartment_id
            )
            
            # Get VCNs for deeper analysis
            vcns = self.client.list_vcns(compartment_id=compartment_id)
            
            findings = []
            security_score = 100  # Start perfect, deduct for issues
            
            # Analyze public exposure
            if isinstance(public_endpoints, list):
                for endpoint in public_endpoints:
                    public_count = endpoint.get("public_subnets", 0)
                    total_count = endpoint.get("total_subnets", 0)
                    vcn_name = endpoint.get("vcn", "Unknown")
                    
                    exposure_ratio = (public_count / total_count * 100) if total_count > 0 else 0
                    
                    if exposure_ratio > 50:
                        findings.append({
                            "severity": "high",
                            "type": "public_exposure",
                            "vcn": vcn_name,
                            "description": f"{exposure_ratio:.0f}% of subnets are public",
                            "recommendation": "Review if all public subnets are necessary"
                        })
                        security_score -= 15
                    elif exposure_ratio > 30:
                        findings.append({
                            "severity": "medium",
                            "type": "public_exposure",
                            "vcn": vcn_name,
                            "description": f"{exposure_ratio:.0f}% of subnets are public",
                            "recommendation": "Consider reducing public subnet count"
                        })
                        security_score -= 10
            
            # Check for VCNs with only public subnets
            if isinstance(vcns, list):
                for vcn in vcns:
                    vcn_id = vcn.get("id")
                    vcn_name = vcn.get("display_name")
                    
                    subnets = self.client.list_subnets(
                        vcn_id=vcn_id,
                        compartment_id=compartment_id
                    )
                    
                    if isinstance(subnets, list) and len(subnets) > 0:
                        all_public = all(
                            not s.get("prohibit_public_ip_on_vnic", True)
                            for s in subnets
                        )
                        
                        if all_public:
                            findings.append({
                                "severity": "high",
                                "type": "all_public_network",
                                "vcn": vcn_name,
                                "description": "All subnets allow public IPs",
                                "recommendation": "Add private subnets for backend services"
                            })
                            security_score -= 20
            
            # Ensure minimum score
            security_score = max(0, security_score)
            
            # Determine overall status
            if security_score >= 80:
                status = "good"
            elif security_score >= 60:
                status = "moderate"
            elif security_score >= 40:
                status = "needs_attention"
            else:
                status = "critical"
            
            return {
                "analysis_type": "security_assessment",
                "timestamp": datetime.now().isoformat(),
                "scope": {"compartment_id": compartment_id},
                "security_score": security_score,
                "status": status,
                "findings": findings,
                "findings_by_severity": self._count_by_severity(findings),
                "public_exposure_summary": public_endpoints if isinstance(public_endpoints, list) else [],
                "recommendations": self._generate_security_recommendations(findings, security_score),
                "summary": f"Security score: {security_score}/100 ({status}). {len(findings)} findings detected."
            }
            
        except Exception as e:
            logger.error(f"Error assessing security: {e}")
            return {"error": str(e)}
    
    def _count_by_severity(self, findings: List[Dict]) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in findings:
            severity = finding.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts
    
    def _generate_security_recommendations(
        self,
        findings: List[Dict],
        score: int
    ) -> List[Dict]:
        """Generate security recommendations."""
        recommendations = []
        
        # Priority actions based on findings
        high_severity = [f for f in findings if f.get("severity") in ["critical", "high"]]
        
        if high_severity:
            recommendations.append({
                "priority": "critical",
                "category": "immediate_action",
                "description": f"{len(high_severity)} high-severity security issues found",
                "action": "Address high-severity findings immediately"
            })
        
        # General recommendations based on score
        if score < 60:
            recommendations.append({
                "priority": "high",
                "category": "architecture",
                "description": "Network security posture needs improvement",
                "action": "Review and implement network segmentation best practices"
            })
        
        if score < 80:
            recommendations.append({
                "priority": "medium",
                "category": "review",
                "description": "Schedule regular security reviews",
                "action": "Implement quarterly network security assessments"
            })
        
        return recommendations
    
    def diagnose_connectivity(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Diagnose network connectivity configuration.
        
        Args:
            compartment_id: Optional compartment to diagnose
            
        Returns:
            Connectivity diagnostic results
        """
        try:
            vcns = self.client.list_vcns(compartment_id=compartment_id)
            
            if isinstance(vcns, dict) and "error" in vcns:
                return vcns
            
            diagnostics = {
                "vcn_analysis": [],
                "issues": [],
                "connectivity_matrix": []
            }
            
            # Analyze each VCN
            for vcn in (vcns if isinstance(vcns, list) else []):
                vcn_id = vcn.get("id")
                vcn_name = vcn.get("display_name")
                
                subnets = self.client.list_subnets(
                    vcn_id=vcn_id,
                    compartment_id=compartment_id
                )
                
                vcn_diagnostic = {
                    "vcn_id": vcn_id,
                    "vcn_name": vcn_name,
                    "cidr": vcn.get("cidr_block"),
                    "subnet_count": len(subnets) if isinstance(subnets, list) else 0,
                    "connectivity_status": "healthy",
                    "potential_issues": []
                }
                
                # Check for connectivity issues
                if isinstance(subnets, list):
                    public_count = sum(1 for s in subnets if not s.get("prohibit_public_ip_on_vnic", True))
                    private_count = len(subnets) - public_count
                    
                    # Check for isolated subnets
                    if len(subnets) == 1:
                        vcn_diagnostic["potential_issues"].append({
                            "type": "single_subnet",
                            "severity": "info",
                            "description": "Single subnet may limit connectivity patterns"
                        })
                    
                    # Check for public-only VCN
                    if public_count > 0 and private_count == 0:
                        vcn_diagnostic["potential_issues"].append({
                            "type": "no_private_subnet",
                            "severity": "warning",
                            "description": "No private subnets for backend communication"
                        })
                        vcn_diagnostic["connectivity_status"] = "attention_needed"
                    
                    # Check for private-only VCN
                    if private_count > 0 and public_count == 0:
                        vcn_diagnostic["potential_issues"].append({
                            "type": "no_public_subnet",
                            "severity": "info",
                            "description": "No public subnets - verify NAT/Service Gateway for outbound"
                        })
                
                if vcn_diagnostic["potential_issues"]:
                    diagnostics["issues"].extend([
                        {**issue, "vcn": vcn_name}
                        for issue in vcn_diagnostic["potential_issues"]
                    ])
                
                diagnostics["vcn_analysis"].append(vcn_diagnostic)
            
            # Overall connectivity assessment
            total_issues = len(diagnostics["issues"])
            if total_issues == 0:
                status = "healthy"
            elif any(i.get("severity") == "warning" for i in diagnostics["issues"]):
                status = "attention_needed"
            else:
                status = "healthy_with_notes"
            
            return {
                "analysis_type": "connectivity_diagnosis",
                "timestamp": datetime.now().isoformat(),
                "scope": {"compartment_id": compartment_id},
                "overall_status": status,
                "vcn_count": len(vcns) if isinstance(vcns, list) else 0,
                "diagnostics": diagnostics,
                "recommendations": self._generate_connectivity_recommendations(diagnostics),
                "summary": f"Connectivity status: {status}. {total_issues} potential issues identified."
            }
            
        except Exception as e:
            logger.error(f"Error diagnosing connectivity: {e}")
            return {"error": str(e)}
    
    def _generate_connectivity_recommendations(
        self,
        diagnostics: Dict
    ) -> List[Dict]:
        """Generate connectivity recommendations."""
        recommendations = []
        issues = diagnostics.get("issues", [])
        
        # Check for missing private subnets
        no_private = [i for i in issues if i.get("type") == "no_private_subnet"]
        if no_private:
            recommendations.append({
                "priority": "medium",
                "category": "architecture",
                "description": f"{len(no_private)} VCNs lack private subnets",
                "action": "Add private subnets for internal service communication"
            })
        
        # Check for single subnet VCNs
        single_subnet = [i for i in issues if i.get("type") == "single_subnet"]
        if single_subnet:
            recommendations.append({
                "priority": "low",
                "category": "design",
                "description": f"{len(single_subnet)} VCNs have single subnet",
                "action": "Consider adding subnets for better network isolation"
            })
        
        return recommendations
    
    def generate_network_report(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive network diagnostic report.
        
        Args:
            compartment_id: Optional compartment scope
            
        Returns:
            Full network report with all analyses
        """
        try:
            # Run all analyses
            topology = self.analyze_topology(compartment_id)
            security = self.assess_security(compartment_id)
            connectivity = self.diagnose_connectivity(compartment_id)
            
            # Aggregate recommendations
            all_recommendations = []
            
            if "recommendations" in topology:
                all_recommendations.extend(topology.get("topology", {}).get("recommendations", []))
            if "recommendations" in security:
                all_recommendations.extend(security["recommendations"])
            if "recommendations" in connectivity:
                all_recommendations.extend(connectivity["recommendations"])
            
            # Prioritize
            prioritized = sorted(
                all_recommendations,
                key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.get("priority"), 4)
            )
            
            # Calculate overall health score
            security_score = security.get("security_score", 50)
            connectivity_status = connectivity.get("overall_status", "healthy")
            
            connectivity_score = {
                "healthy": 100,
                "healthy_with_notes": 85,
                "attention_needed": 60,
                "critical": 30
            }.get(connectivity_status, 50)
            
            overall_score = (security_score + connectivity_score) / 2
            
            return {
                "report_type": "network_diagnostics",
                "generated_at": datetime.now().isoformat(),
                "scope": {"compartment_id": compartment_id},
                "executive_summary": self._generate_network_summary(topology, security, connectivity),
                "overall_health_score": round(overall_score, 1),
                "topology_analysis": topology,
                "security_assessment": security,
                "connectivity_diagnosis": connectivity,
                "prioritized_recommendations": prioritized[:10],
                "metrics": {
                    "total_vcns": topology.get("topology", {}).get("total_vcns", 0),
                    "total_subnets": topology.get("topology", {}).get("total_subnets", 0),
                    "security_score": security_score,
                    "connectivity_status": connectivity_status
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating network report: {e}")
            return {"error": str(e)}
    
    def _generate_network_summary(
        self,
        topology: Dict,
        security: Dict,
        connectivity: Dict
    ) -> str:
        """Generate executive summary for network report."""
        parts = []
        
        # Topology summary
        topo = topology.get("topology", {})
        parts.append(f"Network: {topo.get('total_vcns', 0)} VCNs, {topo.get('total_subnets', 0)} subnets")
        
        # Security summary
        security_score = security.get("security_score", 0)
        security_status = security.get("status", "unknown")
        parts.append(f"Security: {security_score}/100 ({security_status})")
        
        # Connectivity summary
        conn_status = connectivity.get("overall_status", "unknown")
        parts.append(f"Connectivity: {conn_status}")
        
        return ". ".join(parts)
