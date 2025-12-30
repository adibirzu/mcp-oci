"""OCI Security domain tool implementations.

Provides IAM, Cloud Guard, and security policy management tools.
Follows OCI MCP Server Standard v2.1 with FastMCP patterns.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from mcp_server_oci.core.client import oci_client_manager
from mcp_server_oci.core.errors import format_error_response, handle_oci_error
from mcp_server_oci.skills.discovery import auto_register_tool

from .formatters import SecurityFormatter
from .models import (
    GetUserInput,
    ListCloudGuardProblemsInput,
    ListGroupsInput,
    ListPoliciesInput,
    ListUsersInput,
    ResponseFormat,
    SecurityAuditInput,
)


def register_security_tools(mcp: FastMCP) -> None:
    """Register all security domain tools with the MCP server."""

    @mcp.tool(
        name="oci_security_list_users",
        annotations={
            "title": "List IAM Users",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_users(params: ListUsersInput, ctx: Context) -> str:
        """List IAM users in the tenancy or compartment.

        Retrieves users with optional filtering by lifecycle state or name.

        Args:
            params: ListUsersInput with compartment_id, lifecycle_state, name_contains, limit

        Returns:
            User list in requested format (markdown or json)

        Example:
            {"lifecycle_state": "ACTIVE", "limit": 20}
        """
        await ctx.report_progress(0.1, "Connecting to OCI Identity service...")

        try:
            client = oci_client_manager.identity

            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            await ctx.report_progress(0.3, "Fetching users...")

            response = await asyncio.to_thread(
                client.list_users,
                compartment_id=compartment_id,
                lifecycle_state=params.lifecycle_state.value if params.lifecycle_state else None,
                limit=params.limit,
            )

            users = response.data

            # Filter by name if specified
            if params.name_contains:
                users = [u for u in users if params.name_contains.lower() in u.name.lower()]

            await ctx.report_progress(0.8, "Formatting response...")

            data = {
                "total": len(users),
                "compartment_name": "Tenancy Root" if compartment_id == oci_client_manager.tenancy_id else compartment_id,
                "users": [
                    {
                        "id": u.id,
                        "name": u.name,
                        "email": u.email,
                        "lifecycle_state": u.lifecycle_state,
                        "time_created": str(u.time_created) if u.time_created else None,
                        "description": u.description,
                    }
                    for u in users[:params.limit]
                ],
            }

            if params.response_format == ResponseFormat.JSON:
                return SecurityFormatter.to_json(data)
            return SecurityFormatter.users_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "listing users")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_security_list_users",
        domain="security",
        func=list_users,
        tier=2,
    )

    @mcp.tool(
        name="oci_security_get_user",
        annotations={
            "title": "Get User Details",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def get_user(params: GetUserInput, ctx: Context) -> str:
        """Get detailed information about a specific IAM user.

        Retrieves user details including optional group memberships and API keys.

        Args:
            params: GetUserInput with user_id, include_groups, include_api_keys

        Returns:
            User details in requested format

        Example:
            {"user_id": "ocid1.user.oc1..xxx", "include_groups": true}
        """
        await ctx.report_progress(0.1, "Fetching user details...")

        try:
            client = oci_client_manager.identity

            response = await asyncio.to_thread(client.get_user, user_id=params.user_id)
            user = response.data

            await ctx.report_progress(0.4, "Processing user data...")

            data: dict[str, Any] = {
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "lifecycle_state": user.lifecycle_state,
                    "time_created": str(user.time_created) if user.time_created else None,
                    "description": user.description,
                    "compartment_id": user.compartment_id,
                },
            }

            # Fetch group memberships
            if params.include_groups:
                await ctx.report_progress(0.6, "Fetching group memberships...")
                groups_response = await asyncio.to_thread(
                    client.list_user_group_memberships,
                    compartment_id=user.compartment_id,
                    user_id=user.id,
                )

                group_ids = [m.group_id for m in groups_response.data]
                groups = []
                for group_id in group_ids:
                    group_response = await asyncio.to_thread(client.get_group, group_id=group_id)
                    groups.append({"id": group_response.data.id, "name": group_response.data.name})
                data["groups"] = groups

            # Fetch API keys
            if params.include_api_keys:
                await ctx.report_progress(0.8, "Fetching API keys...")
                keys_response = await asyncio.to_thread(
                    client.list_api_keys,
                    user_id=user.id,
                )
                data["api_keys"] = [
                    {
                        "key_id": k.key_id,
                        "fingerprint": k.fingerprint,
                        "lifecycle_state": k.lifecycle_state,
                        "time_created": str(k.time_created) if k.time_created else None,
                    }
                    for k in keys_response.data
                ]

            if params.response_format == ResponseFormat.JSON:
                return SecurityFormatter.to_json(data)
            return SecurityFormatter.user_detail_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "getting user details")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_security_get_user",
        domain="security",
        func=get_user,
        tier=2,
    )

    @mcp.tool(
        name="oci_security_list_groups",
        annotations={
            "title": "List IAM Groups",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_groups(params: ListGroupsInput, ctx: Context) -> str:
        """List IAM groups in the tenancy.

        Args:
            params: ListGroupsInput with name_contains, limit

        Returns:
            Groups list in requested format
        """
        await ctx.report_progress(0.1, "Fetching IAM groups...")

        try:
            client = oci_client_manager.identity
            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            response = await asyncio.to_thread(
                client.list_groups,
                compartment_id=compartment_id,
                limit=params.limit,
            )

            groups = response.data

            if params.name_contains:
                groups = [g for g in groups if params.name_contains.lower() in g.name.lower()]

            data = {
                "total": len(groups),
                "groups": [
                    {
                        "id": g.id,
                        "name": g.name,
                        "description": g.description,
                        "time_created": str(g.time_created) if g.time_created else None,
                    }
                    for g in groups[:params.limit]
                ],
            }

            if params.response_format == ResponseFormat.JSON:
                return SecurityFormatter.to_json(data)
            return SecurityFormatter.groups_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "listing groups")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_security_list_groups",
        domain="security",
        func=list_groups,
        tier=2,
    )

    @mcp.tool(
        name="oci_security_list_policies",
        annotations={
            "title": "List IAM Policies",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_policies(params: ListPoliciesInput, ctx: Context) -> str:
        """List IAM policies in a compartment.

        Args:
            params: ListPoliciesInput with compartment_id, name_contains, limit

        Returns:
            Policies list with statements in requested format
        """
        await ctx.report_progress(0.1, "Fetching IAM policies...")

        try:
            client = oci_client_manager.identity
            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            response = await asyncio.to_thread(
                client.list_policies,
                compartment_id=compartment_id,
                limit=params.limit,
            )

            policies = response.data

            if params.name_contains:
                policies = [p for p in policies if params.name_contains.lower() in p.name.lower()]

            data = {
                "total": len(policies),
                "compartment_name": compartment_id,
                "policies": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "statements": p.statements,
                        "time_created": str(p.time_created) if p.time_created else None,
                    }
                    for p in policies[:params.limit]
                ],
            }

            if params.response_format == ResponseFormat.JSON:
                return SecurityFormatter.to_json(data)
            return SecurityFormatter.policies_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "listing policies")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_security_list_policies",
        domain="security",
        func=list_policies,
        tier=2,
    )

    @mcp.tool(
        name="oci_security_list_cloud_guard_problems",
        annotations={
            "title": "List Cloud Guard Problems",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_cloud_guard_problems(params: ListCloudGuardProblemsInput, ctx: Context) -> str:
        """List Cloud Guard security problems.

        Retrieves detected security problems with optional filtering by risk level.

        Args:
            params: ListCloudGuardProblemsInput with risk_level, lifecycle_state, limit

        Returns:
            Problems list with risk summary in requested format
        """
        await ctx.report_progress(0.1, "Connecting to Cloud Guard...")

        try:
            from oci.cloud_guard import CloudGuardClient

            config = oci_client_manager._config
            cloud_guard = CloudGuardClient(config, signer=oci_client_manager._signer)

            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            await ctx.report_progress(0.3, "Fetching Cloud Guard problems...")

            response = await asyncio.to_thread(
                cloud_guard.list_problems,
                compartment_id=compartment_id,
                lifecycle_state=params.lifecycle_state.value if params.lifecycle_state else None,
                risk_level=params.risk_level.value if params.risk_level else None,
                limit=params.limit,
            )

            problems = response.data.items

            await ctx.report_progress(0.7, "Processing problems...")

            # Calculate risk summary
            risk_counts = Counter(p.risk_level for p in problems)

            data = {
                "total": len(problems),
                "summary": dict(risk_counts),
                "problems": [
                    {
                        "id": p.id,
                        "problem_name": p.detector_rule_id,
                        "risk_level": p.risk_level,
                        "resource_name": p.resource_name,
                        "resource_type": p.resource_type,
                        "region": p.region,
                        "time_first_detected": str(p.time_first_detected) if p.time_first_detected else None,
                        "recommendation": p.recommendation if hasattr(p, "recommendation") else None,
                    }
                    for p in problems[:params.limit]
                ],
            }

            if params.response_format == ResponseFormat.JSON:
                return SecurityFormatter.to_json(data)
            return SecurityFormatter.cloud_guard_problems_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "listing Cloud Guard problems")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_security_list_cloud_guard_problems",
        domain="security",
        func=list_cloud_guard_problems,
        tier=2,
    )

    @mcp.tool(
        name="oci_security_audit",
        annotations={
            "title": "Security Audit",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def security_audit(params: SecurityAuditInput, ctx: Context) -> str:
        """Perform a comprehensive security audit.

        Analyzes IAM configuration, Cloud Guard problems, and network security
        to provide a security posture assessment.

        Args:
            params: SecurityAuditInput with scope options

        Returns:
            Security audit report with score and recommendations
        """
        await ctx.report_progress(0.1, "Starting security audit...")

        try:
            compartment_id = params.compartment_id or oci_client_manager.tenancy_id

            data: dict[str, Any] = {
                "audit_time": datetime.now(timezone.utc).isoformat(),
                "compartment_name": "Tenancy Root" if compartment_id == oci_client_manager.tenancy_id else compartment_id,
                "security_score": {"overall": 0},
                "recommendations": [],
            }

            score_components = []

            # IAM Analysis
            if params.include_iam:
                await ctx.report_progress(0.2, "Analyzing IAM configuration...")

                identity = oci_client_manager.identity

                users_resp = await asyncio.to_thread(
                    identity.list_users,
                    compartment_id=compartment_id,
                )
                groups_resp = await asyncio.to_thread(
                    identity.list_groups,
                    compartment_id=compartment_id,
                )
                policies_resp = await asyncio.to_thread(
                    identity.list_policies,
                    compartment_id=compartment_id,
                )

                users = users_resp.data
                active_users = [u for u in users if u.lifecycle_state == "ACTIVE"]

                iam_findings = []

                # Check for users without MFA (simplified check)
                if len(active_users) > 0:
                    iam_findings.append(f"Review MFA status for {len(active_users)} active users")

                # Check for overly permissive policies
                broad_policies = [
                    p for p in policies_resp.data
                    if any("manage all-resources" in s.lower() for s in p.statements)
                ]
                if broad_policies:
                    iam_findings.append(f"{len(broad_policies)} policies with 'manage all-resources' detected")

                data["iam_summary"] = {
                    "total_users": len(users),
                    "active_users": len(active_users),
                    "total_groups": len(groups_resp.data),
                    "total_policies": len(policies_resp.data),
                    "findings": iam_findings,
                }

                iam_score = 80 if not iam_findings else 60
                score_components.append(iam_score)

            # Cloud Guard Analysis
            if params.include_cloud_guard:
                await ctx.report_progress(0.5, "Analyzing Cloud Guard findings...")

                try:
                    from oci.cloud_guard import CloudGuardClient

                    config = oci_client_manager._config
                    cloud_guard = CloudGuardClient(config, signer=oci_client_manager._signer)

                    problems_resp = await asyncio.to_thread(
                        cloud_guard.list_problems,
                        compartment_id=compartment_id,
                        lifecycle_state="ACTIVE",
                        limit=100,
                    )

                    problems = problems_resp.data.items
                    critical = sum(1 for p in problems if p.risk_level == "CRITICAL")
                    high = sum(1 for p in problems if p.risk_level == "HIGH")
                    medium = sum(1 for p in problems if p.risk_level == "MEDIUM")

                    data["cloud_guard_summary"] = {
                        "total": len(problems),
                        "critical": critical,
                        "high": high,
                        "medium": medium,
                    }

                    if critical > 0:
                        data["recommendations"].append(f"Address {critical} critical Cloud Guard problems immediately")

                    cg_score = 90 if critical == 0 and high == 0 else 70 if critical == 0 else 40
                    score_components.append(cg_score)

                except Exception:
                    data["cloud_guard_summary"] = {"error": "Cloud Guard not enabled or accessible"}
                    score_components.append(50)

            # Network Security Analysis
            if params.include_network_security:
                await ctx.report_progress(0.7, "Analyzing network security...")

                try:
                    network = oci_client_manager.virtual_network

                    vcns_resp = await asyncio.to_thread(
                        network.list_vcns,
                        compartment_id=compartment_id,
                    )

                    network_findings = []
                    public_subnets = 0
                    open_rules = 0

                    for vcn in vcns_resp.data[:10]:  # Limit analysis
                        subnets_resp = await asyncio.to_thread(
                            network.list_subnets,
                            compartment_id=compartment_id,
                            vcn_id=vcn.id,
                        )

                        for subnet in subnets_resp.data:
                            if not subnet.prohibit_public_ip_on_vnic:
                                public_subnets += 1

                    if public_subnets > 5:
                        network_findings.append(f"{public_subnets} public subnets detected - review necessity")

                    data["network_summary"] = {
                        "total_vcns": len(vcns_resp.data),
                        "public_subnets": public_subnets,
                        "open_rules": open_rules,
                        "findings": network_findings,
                    }

                    net_score = 85 if not network_findings else 65
                    score_components.append(net_score)

                except Exception:
                    data["network_summary"] = {"error": "Network analysis failed"}
                    score_components.append(50)

            # Calculate overall score
            if score_components:
                data["security_score"]["overall"] = int(sum(score_components) / len(score_components))

            # Add general recommendations
            if data["security_score"]["overall"] < 70:
                data["recommendations"].append("Review security configuration as overall score is below threshold")

            await ctx.report_progress(0.9, "Generating report...")

            if params.response_format == ResponseFormat.JSON:
                return SecurityFormatter.to_json(data)
            return SecurityFormatter.security_audit_markdown(data)

        except Exception as e:
            error = handle_oci_error(e, "performing security audit")
            return format_error_response(error, params.response_format.value)

    auto_register_tool(
        name="oci_security_audit",
        domain="security",
        func=security_audit,
        tier=3,
    )
