#!/usr/bin/env python3
"""
Optimized IAM MCP Server
Based on official OCI Python SDK patterns and shared architecture
"""

from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    FastMCP = None  # type: ignore
    _import_error = e
else:
    _import_error = None

from .shared_architecture import (
    OCIResponse,
    clients,
    create_common_tools,
    format_for_llm,
    handle_oci_error,
    validate_compartment_id,
)


def run_iam(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_iam") -> None:
    """Serve an optimized FastMCP app for IAM operations."""
    if FastMCP is None:
        raise SystemExit(
            f"fastmcp is not installed. Install with: pip install fastmcp\nOriginal import error: {_import_error}"
        )

    # Set environment variables if provided
    if profile:
        import os
        os.environ["OCI_PROFILE"] = profile
    if region:
        import os
        os.environ["OCI_REGION"] = region

    app = FastMCP(server_name)

    # Create common tools
    create_common_tools(app, server_name)

    # IAM-specific tools
    @app.tool()
    async def list_users(
        compartment_id: str | None = None,
        name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List users using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            identity_client = clients.identity
            
            # Use official OCI SDK method pattern
            response = identity_client.list_users(
                compartment_id=compartment_id,
                name=name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            users = []
            for user in response.data:
                users.append({
                    "id": user.id,
                    "name": user.name,
                    "description": user.description,
                    "lifecycle_state": user.lifecycle_state,
                    "time_created": user.time_created.isoformat() if user.time_created else None,
                    "compartment_id": user.compartment_id,
                    "email": getattr(user, 'email', None),
                    "inactive_status": getattr(user, 'inactive_status', None)
                })
            
            formatted_users = format_for_llm(users, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_users)} users",
                data=formatted_users,
                count=len(formatted_users),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_users", "identity")
            return result.to_dict()

    @app.tool()
    async def get_user(user_id: str) -> str:
        """Get a specific user by ID."""
        try:
            if not user_id.startswith("ocid1.user."):
                raise ValueError("Invalid user ID format")
            
            identity_client = clients.identity
            response = identity_client.get_user(user_id=user_id)
            
            user = {
                "id": response.data.id,
                "name": response.data.name,
                "description": response.data.description,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "email": getattr(response.data, 'email', None),
                "inactive_status": getattr(response.data, 'inactive_status', None)
            }
            
            formatted_user = format_for_llm(user)
            
            result = OCIResponse(
                success=True,
                message="User retrieved successfully",
                data=formatted_user,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_user", "identity")
            return result.to_dict()

    @app.tool()
    async def list_groups(
        compartment_id: str | None = None,
        name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List groups using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            identity_client = clients.identity
            
            # Use official OCI SDK method pattern
            response = identity_client.list_groups(
                compartment_id=compartment_id,
                name=name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            groups = []
            for group in response.data:
                groups.append({
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "lifecycle_state": group.lifecycle_state,
                    "time_created": group.time_created.isoformat() if group.time_created else None,
                    "compartment_id": group.compartment_id
                })
            
            formatted_groups = format_for_llm(groups, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_groups)} groups",
                data=formatted_groups,
                count=len(formatted_groups),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_groups", "identity")
            return result.to_dict()

    @app.tool()
    async def get_group(group_id: str) -> str:
        """Get a specific group by ID."""
        try:
            if not group_id.startswith("ocid1.group."):
                raise ValueError("Invalid group ID format")
            
            identity_client = clients.identity
            response = identity_client.get_group(group_id=group_id)
            
            group = {
                "id": response.data.id,
                "name": response.data.name,
                "description": response.data.description,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id
            }
            
            formatted_group = format_for_llm(group)
            
            result = OCIResponse(
                success=True,
                message="Group retrieved successfully",
                data=formatted_group,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_group", "identity")
            return result.to_dict()

    @app.tool()
    async def list_policies(
        compartment_id: str | None = None,
        name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List policies using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            identity_client = clients.identity
            
            # Use official OCI SDK method pattern
            response = identity_client.list_policies(
                compartment_id=compartment_id,
                name=name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            policies = []
            for policy in response.data:
                policies.append({
                    "id": policy.id,
                    "name": policy.name,
                    "description": policy.description,
                    "lifecycle_state": policy.lifecycle_state,
                    "time_created": policy.time_created.isoformat() if policy.time_created else None,
                    "compartment_id": policy.compartment_id,
                    "statements": getattr(policy, 'statements', [])
                })
            
            formatted_policies = format_for_llm(policies, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_policies)} policies",
                data=formatted_policies,
                count=len(formatted_policies),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_policies", "identity")
            return result.to_dict()

    @app.tool()
    async def get_policy(policy_id: str) -> str:
        """Get a specific policy by ID."""
        try:
            if not policy_id.startswith("ocid1.policy."):
                raise ValueError("Invalid policy ID format")
            
            identity_client = clients.identity
            response = identity_client.get_policy(policy_id=policy_id)
            
            policy = {
                "id": response.data.id,
                "name": response.data.name,
                "description": response.data.description,
                "lifecycle_state": response.data.lifecycle_state,
                "time_created": response.data.time_created.isoformat() if response.data.time_created else None,
                "compartment_id": response.data.compartment_id,
                "statements": getattr(response.data, 'statements', [])
            }
            
            formatted_policy = format_for_llm(policy)
            
            result = OCIResponse(
                success=True,
                message="Policy retrieved successfully",
                data=formatted_policy,
                compartment_id=response.data.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_policy", "identity")
            return result.to_dict()

    app.run()
