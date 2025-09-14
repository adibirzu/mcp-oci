# OCI Compute Server

Exposes `oci:compute:*` tools for instances, images, and VNICs.

## Tools
- `oci:compute:list-instances` — List instances in a compartment.
- `oci:compute:get-instance` — Get instance details.
- `oci:compute:list-images` — List images.
- `oci:compute:list-vnics` — List VNIC attachments for an instance.

## Usage
Serve:
```
mcp-oci-serve-compute --profile DEFAULT --region us-phoenix-1
```
