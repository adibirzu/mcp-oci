# mcp_oci_compute

## Overview
OCI Compute MCP server, exposing read tools for instances, images, and VNICs.

## Installation
```
make setup
```

## Configuration
Use `~/.oci/config` or env vars. Defaults can be provided with `mcp-oci-serve --profile/--region`.

## Tools / Resources
- `oci:compute:list-instances` — List instances in a compartment.
- `oci:compute:get-instance` — Get instance details.
- `oci:compute:list-images` — List images in a compartment (filter by OS/version).
- `oci:compute:list-vnics` — List VNIC attachments for an instance.
- `oci:compute:list-shapes` — List shapes (optionally by AD/image).
- `oci:compute:instance-action` — Mutating. START/STOP/RESET (confirm/dry_run supported).
- `oci:compute:list-boot-volumes` — List boot volumes (Blockstorage; requires AD).
- `oci:compute:list-instance-configurations` — List instance configurations (Compute Management).

## Usage
Serve:
```
mcp-oci-serve-compute --profile DEFAULT --region us-phoenix-1
```
Dev calls:
```
mcp-oci call compute oci:compute:list-instances --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call compute oci:compute:get-instance --params '{"instance_id":"ocid1.instance..."}'
mcp-oci call compute oci:compute:list-shapes --params '{"compartment_id":"ocid1.compartment..."}'
mcp-oci call compute oci:compute:list-vnics --params '{"compartment_id":"ocid1.compartment...","instance_id":"ocid1.instance..."}'
mcp-oci call compute oci:compute:list-boot-volumes --params '{"compartment_id":"ocid1.compartment...","availability_domain":"phx-AD-1"}'
mcp-oci call compute oci:compute:list-instance-configurations --params '{"compartment_id":"ocid1.compartment..."}'
\# Dry run then confirm a mutating call
mcp-oci call compute oci:compute:instance-action --params '{"instance_id":"ocid1.instance...","action":"STOP","dry_run":true}'
mcp-oci call compute oci:compute:instance-action --params '{"instance_id":"ocid1.instance...","action":"STOP","confirm":true}'
```

### Example Host Config (MCP)
```json
{
  "mcpServers": {
    "oci-compute": {
      "command": "mcp-oci-serve-compute",
      "args": ["--profile", "DEFAULT", "--region", "us-ashburn-1"]
    }
  }
}
```

### Example Transcript
```
> tools/call name=oci:compute:list-shapes arguments={"compartment_id":"ocid1.compartment..."}
< { "content": [ { "type": "json", "json": { "items": [ { "shape": "VM.Standard.E5.Flex" } ] } } ] }
```

## Next
See ../../docs/SERVERS.md for all OCI MCP servers.
