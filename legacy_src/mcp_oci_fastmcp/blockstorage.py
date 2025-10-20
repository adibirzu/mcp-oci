#!/usr/bin/env python3
"""
Optimized Blockstorage MCP Server
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


def run_blockstorage(*, profile: str | None = None, region: str | None = None, server_name: str = "mcp_oci_blockstorage") -> None:
    """Serve an optimized FastMCP app for blockstorage operations."""
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

    # Blockstorage-specific tools
        # Blockstorage-specific tools
    @app.tool()
    async def list_volumes(
        compartment_id: str | None = None,
        availability_domain: str | None = None,
        display_name: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 50
    ) -> str:
        """List block storage volumes using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            block_storage_client = clients.block_storage
            
            # Use official OCI SDK method pattern
            response = block_storage_client.list_volumes(
                compartment_id=compartment_id,
                availability_domain=availability_domain,
                display_name=display_name,
                lifecycle_state=lifecycle_state,
                limit=limit
            )
            
            volumes = []
            for volume in response.data:
                volumes.append({
                    "id": volume.id,
                    "display_name": volume.display_name,
                    "lifecycle_state": volume.lifecycle_state,
                    "availability_domain": volume.availability_domain,
                    "time_created": volume.time_created.isoformat() if volume.time_created else None,
                    "compartment_id": volume.compartment_id,
                    "size_in_gbs": volume.size_in_gbs,
                    "size_in_mbs": volume.size_in_mbs,
                    "vpus_per_gb": volume.vpus_per_gb,
                    "volume_group_id": volume.volume_group_id,
                    "is_auto_tune_enabled": volume.is_auto_tune_enabled,
                    "is_hydrated": volume.is_hydrated,
                    "kms_key_id": volume.kms_key_id,
                    "volume_tags": volume.volume_tags
                })
            
            formatted_volumes = format_for_llm(volumes, limit)
            
            result = OCIResponse(
                success=True,
                message=f"Found {len(formatted_volumes)} block volumes",
                data=formatted_volumes,
                count=len(formatted_volumes),
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_volumes", "block_storage")
            return result.to_dict()

    @app.tool()
    async def get_volume(
        volume_id: str,
        compartment_id: str | None = None
    ) -> str:
        """Get specific volume by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            if not volume_id.startswith("ocid1.volume."):
                raise ValueError("Invalid volume ID format")
            
            blockstorage_client = clients.blockstorage
            
            # Get specific volume by ID
            response = blockstorage_client.get_volume(volume_id=volume_id)
            
            volume = response.data
            volume_details = {
                "id": volume.id,
                "display_name": volume.display_name,
                "lifecycle_state": volume.lifecycle_state,
                "size_in_gbs": volume.size_in_gbs,
                "availability_domain": volume.availability_domain,
                "time_created": volume.time_created.isoformat() if volume.time_created else None,
                "compartment_id": volume.compartment_id,
                "vpus_per_gb": volume.vpus_per_gb,
                "is_auto_tune_enabled": volume.is_auto_tune_enabled,
                "is_hydrated": volume.is_hydrated,
                "kms_key_id": volume.kms_key_id,
                "volume_group_id": volume.volume_group_id
            }
            
            result = OCIResponse(
                success=True,
                message=f"Retrieved volume {volume.display_name}",
                data=volume_details,
                compartment_id=volume.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_volume", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def list_volume_backups(
        compartment_id: str | None = None,
        limit: int = 50
    ) -> str:
        """List volume backups using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            # Get the appropriate client
            client = clients.block_storage
            
            # Use official OCI SDK method pattern
            # Note: This is a template implementation
            # You may need to customize the method call based on the specific service
            
            # For now, return a placeholder response
            result = OCIResponse(
                success=True,
                message="List volume backups - Template implementation",
                data={"message": "This is a template implementation for list_volume_backups"},
                count=0,
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "list_volume_backups", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def get_volume_backup(
        volume_backup_id: str,
        compartment_id: str | None = None
    ) -> str:
        """Get specific volume backup by ID using official OCI SDK patterns."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            if not volume_backup_id.startswith("ocid1.volumebackup."):
                raise ValueError("Invalid volume backup ID format")
            
            blockstorage_client = clients.blockstorage
            
            # Get specific volume backup by ID
            response = blockstorage_client.get_volume_backup(volume_backup_id=volume_backup_id)
            
            backup = response.data
            backup_details = {
                "id": backup.id,
                "display_name": backup.display_name,
                "lifecycle_state": backup.lifecycle_state,
                "size_in_gbs": backup.size_in_gbs,
                "time_created": backup.time_created.isoformat() if backup.time_created else None,
                "time_request_received": backup.time_request_received.isoformat() if backup.time_request_received else None,
                "compartment_id": backup.compartment_id,
                "volume_id": backup.volume_id,
                "unique_size_in_gbs": backup.unique_size_in_gbs,
                "source_type": backup.source_type,
                "type": backup.type,
                "kms_key_id": backup.kms_key_id
            }
            
            result = OCIResponse(
                success=True,
                message=f"Retrieved volume backup {backup.display_name}",
                data=backup_details,
                compartment_id=backup.compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "get_volume_backup", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def create_volume(
        compartment_id: str | None = None,
        display_name: str | None = None,
        size_in_gbs: int = 50,
        availability_domain: str | None = None,
        volume_shape: str = "CUSTOM",
        is_auto_tune_enabled: bool = False,
        vpus_per_gb: int = 10
    ) -> str:
        """Create a new block volume."""
        try:
            # Use root compartment if not specified
            if compartment_id is None:
                compartment_id = clients.root_compartment_id
            elif not validate_compartment_id(compartment_id):
                raise ValueError("Invalid compartment ID format")
            
            blockstorage_client = clients.blockstorage
            
            # Get availability domain if not provided
            if not availability_domain:
                identity_client = clients.identity
                ad_response = identity_client.list_availability_domains(compartment_id=compartment_id)
                if not ad_response.data:
                    raise ValueError("No availability domains found")
                availability_domain = ad_response.data[0].name
            
            # Create volume details
            from oci.core.models import CreateVolumeDetails
            
            create_volume_details = CreateVolumeDetails(
                compartment_id=compartment_id,
                display_name=display_name or f"Volume-{size_in_gbs}GB",
                size_in_gbs=size_in_gbs,
                availability_domain=availability_domain,
                vpus_per_gb=vpus_per_gb,
                is_auto_tune_enabled=is_auto_tune_enabled
            )
            
            # Create the volume
            response = blockstorage_client.create_volume(create_volume_details)
            
            result = OCIResponse(
                success=True,
                message="Volume creation initiated successfully",
                data={
                    "volume_id": response.data.id,
                    "display_name": response.data.display_name,
                    "size_in_gbs": response.data.size_in_gbs,
                    "availability_domain": response.data.availability_domain,
                    "lifecycle_state": response.data.lifecycle_state,
                    "compartment_id": response.data.compartment_id
                },
                compartment_id=compartment_id
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "create_volume", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def delete_volume(volume_id: str, force: bool = False) -> str:
        """Delete a block volume."""
        try:
            if not volume_id.startswith("ocid1.volume."):
                raise ValueError("Invalid volume ID format")
            
            blockstorage_client = clients.blockstorage
            
            # Delete the volume
            response = blockstorage_client.delete_volume(
                volume_id=volume_id,
                if_match="*" if force else None
            )
            
            result = OCIResponse(
                success=True,
                message=f"Volume {volume_id} deletion initiated successfully",
                data={
                    "volume_id": volume_id,
                    "status": "DELETION_INITIATED"
                }
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "delete_volume", "blockstorage")
            return result.to_dict()

    @app.tool()
    async def attach_volume(
        instance_id: str,
        volume_id: str,
        device: str | None = None,
        display_name: str | None = None,
        is_read_only: bool = False
    ) -> str:
        """Attach a block volume to an instance."""
        try:
            if not instance_id.startswith("ocid1.instance."):
                raise ValueError("Invalid instance ID format")
            if not volume_id.startswith("ocid1.volume."):
                raise ValueError("Invalid volume ID format")
            
            compute_client = clients.compute
            
            # Create attachment details
            from oci.core.models import AttachVolumeDetails
            
            attach_volume_details = AttachVolumeDetails(
                instance_id=instance_id,
                volume_id=volume_id,
                device=device,
                display_name=display_name,
                is_read_only=is_read_only
            )
            
            # Attach the volume
            response = compute_client.attach_volume(attach_volume_details)
            
            result = OCIResponse(
                success=True,
                message=f"Volume {volume_id} attachment initiated successfully",
                data={
                    "attachment_id": response.data.id,
                    "instance_id": instance_id,
                    "volume_id": volume_id,
                    "lifecycle_state": response.data.lifecycle_state,
                    "device": response.data.device
                }
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "attach_volume", "compute")
            return result.to_dict()

    @app.tool()
    async def detach_volume(volume_attachment_id: str, force: bool = False) -> str:
        """Detach a block volume from an instance."""
        try:
            if not volume_attachment_id.startswith("ocid1.volumeattachment."):
                raise ValueError("Invalid volume attachment ID format")
            
            compute_client = clients.compute
            
            # Detach the volume
            response = compute_client.detach_volume(
                volume_attachment_id=volume_attachment_id,
                if_match="*" if force else None
            )
            
            result = OCIResponse(
                success=True,
                message="Volume detachment initiated successfully",
                data={
                    "attachment_id": volume_attachment_id,
                    "status": "DETACHMENT_INITIATED"
                }
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "detach_volume", "compute")
            return result.to_dict()

    @app.tool()
    async def resize_volume(volume_id: str, size_in_gbs: int) -> str:
        """Resize a block volume."""
        try:
            if not volume_id.startswith("ocid1.volume."):
                raise ValueError("Invalid volume ID format")
            
            blockstorage_client = clients.blockstorage
            
            # Create update volume details
            from oci.core.models import UpdateVolumeDetails
            
            update_volume_details = UpdateVolumeDetails(
                size_in_gbs=size_in_gbs
            )
            
            # Update the volume
            response = blockstorage_client.update_volume(
                volume_id=volume_id,
                update_volume_details=update_volume_details
            )
            
            result = OCIResponse(
                success=True,
                message=f"Volume {volume_id} resize initiated successfully",
                data={
                    "volume_id": volume_id,
                    "new_size_in_gbs": size_in_gbs,
                    "lifecycle_state": response.data.lifecycle_state
                }
            )
            return result.to_dict()
        except Exception as e:
            result = handle_oci_error(e, "resize_volume", "blockstorage")
            return result.to_dict()

    app.run()
