# MCP Streamable Terraform Module

This Terraform configuration provisions a VCN, subnet, NSG, internet gateway, and a VM.Standard.E6.Flex instance configured to run MCP servers with `streamable-http` transport.

## Quick Start

1. Generate `terraform.tfvars.json` using the helper script (pulls defaults from `~/.oci/config` when available). The script also captures your current public IP and stores it as a `/32` CIDR for the NSG; override if you need a different source range.
   ```bash
   cd ops/terraform/mcp_streamable
   ./setup.sh
   ```
2. Initialize and apply:
   ```bash
   terraform init
   terraform apply
   ```

After apply, SSH to the instance and run:
```bash
ssh opc@"$(terraform output -raw instance_public_ip)"
cd ~/mcp-oci-cloud
./bootstrap-mcp.sh
```
The bootstrap script prompts for OCI env values (with existing defaults), persists them to `.env`, ensures `MCP_TRANSPORT=streamable-http`, and restarts the Docker composition.
