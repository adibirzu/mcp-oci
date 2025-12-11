"""
Security Posture Skill

High-level skill for assessing OCI security posture with Cloud Guard and IAM analysis.
Maps to security server tools for agent-friendly operations.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityPostureSkill:
    """
    Skill for assessing OCI security posture.
    
    Provides high-level operations:
    - Cloud Guard problem analysis
    - IAM security assessment
    - Risk scoring
    - Compliance recommendations
    """
    
    def __init__(self, client=None):
        """Initialize with optional client adapter."""
        self.client = client
    
    def assess_cloud_guard_posture(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess Cloud Guard security posture.
        
        Returns:
            - risk_score: Overall risk score
            - problem_summary: Problems by severity
            - critical_issues: List of critical problems
            - recommendations: Security recommendations
        """
        try:
            if not self.client:
                return {"error": "No client configured"}
            
            # Get Cloud Guard problems
            problems = self.client.list_cloud_guard_problems(compartment_id) if hasattr(self.client, 'list_cloud_guard_problems') else []
            risk_score_data = self.client.get_cloud_guard_risk_score(compartment_id) if hasattr(self.client, 'get_cloud_guard_risk_score') else {}
            
            if isinstance(problems, dict) and "error" in problems:
                return problems
            
            # Categorize problems by severity
            severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            critical_issues = []
            high_issues = []
            
            for problem in problems:
                severity = problem.get("risk_level", problem.get("severity", "MEDIUM")).upper()
                if severity in severity_counts:
                    severity_counts[severity] += 1
                
                if severity == "CRITICAL":
                    critical_issues.append({
                        "id": problem.get("id"),
                        "name": problem.get("problem_name", problem.get("display_name", "Unknown")),
                        "detector": problem.get("detector_id"),
                        "resource": problem.get("resource_name", problem.get("resource_id")),
                        "recommendation": problem.get("recommendation")
                    })
                elif severity == "HIGH":
                    high_issues.append({
                        "id": problem.get("id"),
                        "name": problem.get("problem_name", problem.get("display_name", "Unknown")),
                        "resource": problem.get("resource_name", problem.get("resource_id"))
                    })
            
            # Calculate security score (inverse of risk)
            total_problems = len(problems)
            security_score = 100
            security_score -= severity_counts["CRITICAL"] * 20
            security_score -= severity_counts["HIGH"] * 10
            security_score -= severity_counts["MEDIUM"] * 3
            security_score -= severity_counts["LOW"] * 1
            security_score = max(0, security_score)
            
            # Generate recommendations
            recommendations = []
            if severity_counts["CRITICAL"] > 0:
                recommendations.append(f"URGENT: Address {severity_counts['CRITICAL']} critical security issues immediately")
            if severity_counts["HIGH"] > 0:
                recommendations.append(f"Address {severity_counts['HIGH']} high-severity issues within 24 hours")
            if total_problems == 0:
                recommendations.append("Excellent! No Cloud Guard problems detected. Continue monitoring.")
            
            # Determine status
            if severity_counts["CRITICAL"] > 0:
                status = "CRITICAL"
            elif severity_counts["HIGH"] > 0:
                status = "WARNING"
            elif total_problems > 0:
                status = "NEEDS_ATTENTION"
            else:
                status = "HEALTHY"
            
            return {
                "analysis_type": "cloud_guard_posture",
                "timestamp": datetime.utcnow().isoformat(),
                "security_score": security_score,
                "status": status,
                "total_problems": total_problems,
                "problem_summary": severity_counts,
                "critical_issues": critical_issues[:5],  # Top 5
                "high_issues": high_issues[:5],
                "recommendations": recommendations,
                "summary": f"Security score: {security_score}, {total_problems} problems ({severity_counts['CRITICAL']} critical, {severity_counts['HIGH']} high)"
            }
            
        except Exception as e:
            logger.error(f"Error assessing Cloud Guard posture: {e}")
            return {"error": str(e), "analysis_type": "cloud_guard_posture"}
    
    def assess_iam_security(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess IAM security configuration.
        
        Returns:
            - user_analysis: User security insights
            - policy_analysis: Policy configuration insights
            - iam_score: IAM security score
            - recommendations: IAM security recommendations
        """
        try:
            if not self.client:
                return {"error": "No client configured"}
            
            # Get IAM data
            users = self.client.list_users(compartment_id) if hasattr(self.client, 'list_users') else []
            groups = self.client.list_groups(compartment_id) if hasattr(self.client, 'list_groups') else []
            policies = self.client.list_policies(compartment_id) if hasattr(self.client, 'list_policies') else []
            
            if isinstance(users, dict) and "error" in users:
                return users
            
            # Analyze users
            total_users = len(users)
            inactive_users = []
            users_without_mfa = []
            
            for user in users:
                lifecycle_state = user.get("lifecycle_state", "ACTIVE")
                if lifecycle_state != "ACTIVE":
                    inactive_users.append(user.get("name", user.get("id")))
                # MFA check would require additional API call
            
            # Analyze policies
            total_policies = len(policies)
            overly_permissive = []
            
            for policy in policies:
                statements = policy.get("statements", [])
                for stmt in statements:
                    stmt_lower = str(stmt).lower()
                    # Flag overly permissive policies
                    if "allow any-user" in stmt_lower or "manage all-resources" in stmt_lower:
                        overly_permissive.append({
                            "policy_name": policy.get("name"),
                            "statement": stmt[:100] + "..." if len(stmt) > 100 else stmt
                        })
            
            # Calculate IAM score
            iam_score = 100
            issues = []
            recommendations = []
            
            if len(inactive_users) > 0:
                iam_score -= len(inactive_users) * 5
                issues.append({
                    "type": "inactive_users",
                    "count": len(inactive_users),
                    "message": f"{len(inactive_users)} inactive users found"
                })
                recommendations.append(f"Review and remove {len(inactive_users)} inactive user accounts")
            
            if len(overly_permissive) > 0:
                iam_score -= len(overly_permissive) * 15
                issues.append({
                    "type": "permissive_policies",
                    "count": len(overly_permissive),
                    "message": f"{len(overly_permissive)} overly permissive policies detected"
                })
                recommendations.append("Review and tighten overly permissive IAM policies")
            
            if total_users > 0 and len(groups) == 0:
                iam_score -= 20
                issues.append({
                    "type": "no_groups",
                    "message": "Users exist but no groups defined - consider group-based access management"
                })
                recommendations.append("Implement group-based access control for better management")
            
            iam_score = max(0, iam_score)
            
            return {
                "analysis_type": "iam_security",
                "timestamp": datetime.utcnow().isoformat(),
                "iam_score": iam_score,
                "user_analysis": {
                    "total_users": total_users,
                    "inactive_users": len(inactive_users),
                    "inactive_user_names": inactive_users[:5]
                },
                "group_analysis": {
                    "total_groups": len(groups)
                },
                "policy_analysis": {
                    "total_policies": total_policies,
                    "overly_permissive_count": len(overly_permissive),
                    "overly_permissive": overly_permissive[:3]
                },
                "issues": issues,
                "recommendations": recommendations,
                "summary": f"IAM score: {iam_score}, {total_users} users, {total_policies} policies"
            }
            
        except Exception as e:
            logger.error(f"Error assessing IAM security: {e}")
            return {"error": str(e), "analysis_type": "iam_security"}
    
    def generate_security_report(
        self,
        compartment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive security posture report.
        
        Combines Cloud Guard and IAM assessments.
        """
        try:
            cloud_guard = self.assess_cloud_guard_posture(compartment_id)
            iam = self.assess_iam_security(compartment_id)
            
            # Calculate overall score
            cg_score = cloud_guard.get("security_score", 0)
            iam_score = iam.get("iam_score", 0)
            overall_score = (cg_score * 0.6 + iam_score * 0.4)  # Weight Cloud Guard higher
            
            # Determine overall status
            if cloud_guard.get("status") == "CRITICAL" or overall_score < 50:
                overall_status = "CRITICAL"
            elif cloud_guard.get("status") == "WARNING" or overall_score < 70:
                overall_status = "WARNING"
            elif overall_score < 90:
                overall_status = "NEEDS_ATTENTION"
            else:
                overall_status = "HEALTHY"
            
            # Combine recommendations
            all_recommendations = []
            all_recommendations.extend(cloud_guard.get("recommendations", []))
            all_recommendations.extend(iam.get("recommendations", []))
            
            return {
                "report_type": "security_posture_report",
                "timestamp": datetime.utcnow().isoformat(),
                "overall_score": round(overall_score, 1),
                "overall_status": overall_status,
                "cloud_guard_assessment": cloud_guard,
                "iam_assessment": iam,
                "executive_summary": {
                    "overall_score": round(overall_score, 1),
                    "status": overall_status,
                    "cloud_guard_score": cg_score,
                    "iam_score": iam_score,
                    "total_issues": cloud_guard.get("total_problems", 0) + len(iam.get("issues", [])),
                    "critical_count": cloud_guard.get("problem_summary", {}).get("CRITICAL", 0)
                },
                "recommendations": all_recommendations,
                "summary": f"Overall security score: {overall_score:.0f}, status: {overall_status}"
            }
            
        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {"error": str(e), "report_type": "security_posture_report"}


# =============================================================================
# Skill Tool Functions (for MCP registration)
# =============================================================================

def skill_assess_cloud_guard_posture(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess Cloud Guard security posture with problem analysis.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Cloud Guard assessment with security score, problems, and recommendations
    """
    from .adapters import get_security_client_adapter
    skill = SecurityPostureSkill(client=get_security_client_adapter())
    return skill.assess_cloud_guard_posture(compartment_id)


def skill_assess_iam_security(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assess IAM security configuration.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        IAM assessment with user/policy analysis and recommendations
    """
    from .adapters import get_security_client_adapter
    skill = SecurityPostureSkill(client=get_security_client_adapter())
    return skill.assess_iam_security(compartment_id)


def skill_generate_security_report(
    compartment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive security posture report.
    
    Args:
        compartment_id: Optional compartment filter
    
    Returns:
        Complete report combining Cloud Guard and IAM assessments
    """
    from .adapters import get_security_client_adapter
    skill = SecurityPostureSkill(client=get_security_client_adapter())
    return skill.generate_security_report(compartment_id)
