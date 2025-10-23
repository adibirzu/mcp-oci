# OCI Deployment Guide for MCP Servers

## Prerequisites
- OCI CLI installed and configured with API key for initial setup (fallback).
- Docker installed for building images.
- kubectl installed for OKE.
- Terraform installed for OKE Terraform option (optional).
- Existing OKE cluster for Kubernetes deployment, or VCN/subnet for new.

## 1. Terraform Streamable HTTP (Compute)
1. `cd ops/terraform/mcp_streamable`
2. `./setup.sh` – detects values from `~/.oci/config` / previous runs and writes `terraform.tfvars.json` (adjust the saved values if you need to override auto-discovered defaults)
3. `terraform init`
4. `terraform apply`
4. Note the `instance_public_ip` output and SSH in: `ssh opc@<public_ip>`
5. Change to the working directory and run the bootstrap helper:
   ```bash
   cd ~/mcp-oci-cloud
   ./bootstrap-mcp.sh
   ```
   Supply the required `KEY=VALUE` pairs when prompted (e.g. `OCI_PROFILE`, `OCI_REGION`, `COMPARTMENT_OCID`). Existing values are shown as defaults on subsequent runs; the script enforces `MCP_TRANSPORT=streamable-http`, writes `.env`, and starts the Docker composition.

Security posture:
- Cloud-init opens `firewalld` ports 7001–7011 and 8000–8011 and the attached NSG mirrors those rules.
- The VM clones this repository, builds the Docker image locally, and runs all MCP services via Docker with streamable HTTP transport.

## 2. Local on OCI VM
1. Launch VM in OCI Compute (e.g., VM.Standard.E6).
2. SSH to VM, install prerequisites: `apt update && apt install python3-pip curl git -y && pip install poetry`.
3. Clone repo: `git clone https://github.com/adibirzu/mcp-oci.git && cd mcp-oci`.
4. Bootstrap: `bash scripts/bootstrap.sh`.
5. Run: `bash run-all-local.sh`.
6. Access: Ports 8000-8010 on VM IP.

**Instance Principals**:
- Create dynamic group including VM instance OCID.
- Policy: Allow dynamic-group to manage services.

**NSG (Security)**:
- The deploy script creates MCP-Servers-NSG with rules for ports 8000-8010 from your IP.

## 3. Docker Local (on VM)
1. Build: `docker build -t mcp-oci .`.
2. Run: `docker run -d -p 8000-8010:8000-8010 --env OCI_CLI_AUTH=instance_principal --env COMPARTMENT_OCID=your-compartment mcp-oci`.
3. Access: Localhost:8000-8010.

## 4. OCI Container Instances
1. Build and push to OCIR: `docker build -t your-repo/mcp-oci . && docker push your-repo/mcp-oci`.
2. Run deploy script: `bash scripts/deploy-oci.sh --type container --tenancy your-tenancy --compartment your-compartment --region your-region`.
3. Access: Via OCI networking (add ingress rules if needed).

## 5. OKE (CLI)
1. Run deploy script: `bash scripts/deploy-oci.sh --type oke --tenancy your-tenancy --compartment your-compartment --region your-region --vcn-id your-vcn --subnet-id your-subnet --availability-domain your-ad`.
2. Access: kubectl port-forward svc/mcp-oci-service 8000:8000 -n default.

## 6. OKE (Terraform)
1. Update ops/terraform/vars.tf with your values.
2. Run deploy script: `bash scripts/deploy-oci.sh --type oke --use-terraform true --tenancy your-tenancy --compartment your-compartment --region your-region --vcn-id your-vcn --subnet-id your-subnet --availability-domain your-ad`.
3. Access: Same as CLI OKE.

**Test Auth**: `oci os bucket list --auth security=instance_principal`.

**Cleanup**: For OKE, `kubectl delete -f ops/oke/ -n default`; for Container, `oci ce container-instance delete --container-instance-id ID`; for local, `pkill -f mcp`.
