# OCI Deployment Guide for MCP Servers

## Prerequisites
- OCI CLI installed and configured with API key for initial setup (fallback).
- Docker installed for building images.
- kubectl installed for OKE.
- Terraform installed for OKE Terraform option (optional).
- Existing OKE cluster for Kubernetes deployment, or VCN/subnet for new.

## 1. Local on OCI VM
1. Launch VM in OCI Compute (e.g., VM.Standard.E2.1).
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

## 2. Docker Local (on VM)
1. Build: `docker build -t mcp-oci .`.
2. Run: `docker run -d -p 8000-8010:8000-8010 --env OCI_CLI_AUTH=instance_principal --env COMPARTMENT_OCID=your-compartment mcp-oci`.
3. Access: Localhost:8000-8010.

## 3. OCI Container Instances
1. Build and push to OCIR: `docker build -t your-repo/mcp-oci . && docker push your-repo/mcp-oci`.
2. Run deploy script: `bash scripts/deploy-oci.sh --type container --tenancy your-tenancy --compartment your-compartment --region your-region`.
3. Access: Via OCI networking (add ingress rules if needed).

## 4. OKE (CLI)
1. Run deploy script: `bash scripts/deploy-oci.sh --type oke --tenancy your-tenancy --compartment your-compartment --region your-region --vcn-id your-vcn --subnet-id your-subnet --availability-domain your-ad`.
2. Access: kubectl port-forward svc/mcp-oci-service 8000:8000 -n default.

## 5. OKE (Terraform)
1. Update ops/terraform/vars.tf with your values.
2. Run deploy script: `bash scripts/deploy-oci.sh --type oke --use-terraform true --tenancy your-tenancy --compartment your-compartment --region your-region --vcn-id your-vcn --subnet-id your-subnet --availability-domain your-ad`.
3. Access: Same as CLI OKE.

**Test Auth**: `oci os bucket list --auth security=instance_principal`.

**Cleanup**: For OKE, `kubectl delete -f ops/oke/ -n default`; for Container, `oci ce container-instance delete --container-instance-id ID`; for local, `pkill -f mcp`.
