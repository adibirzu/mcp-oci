#!/bin/bash

# OCI MCP Servers Deployment Script
# Supports local, Container Instances, and OKE with Terraform option

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}OCI MCP Servers Deployment Script${NC}"

# Default values
DEPLOY_TYPE="local"  # local, container, oke
USE_TERRAFORM="false"  # false, true for OKE
TENANCY_OCID=""
REGION="eu-frankfurt-1"
COMPARTMENT_OCID=""
DYNAMIC_GROUP_NAME="MCP-Dynamic"
# OCI Registry repo and tag (e.g. iad.ocir.io/tenancyns/mcp-oci:latest)
IMAGE_REPO="iad.ocir.io/tenancyns/mcp-oci"
IMAGE_TAG="latest"
CLUSTER_NAME="mcp-oke-cluster"
NAMESPACE="default"
VCN_ID=""
SUBNET_ID=""
AVAILABILITY_DOMAIN="YOUR_AD"
# Auth mode: instance_principal (DG+policies) or config_file (user/API keys via ~/.oci/config)
AUTH_MODE="instance_principal"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      DEPLOY_TYPE="$2"
      shift 2
      ;;
    --use-terraform)
      USE_TERRAFORM="$2"
      shift 2
      ;;
    --tenancy)
      TENANCY_OCID="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --compartment)
      COMPARTMENT_OCID="$2"
      shift 2
      ;;
    --dynamic-group)
      DYNAMIC_GROUP_NAME="$2"
      shift 2
      ;;
    --auth-mode)
      AUTH_MODE="$2"
      shift 2
      ;;
    --image-repo)
      IMAGE_REPO="$2"
      shift 2
      ;;
    --image-tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --cluster)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --vcn-id)
      VCN_ID="$2"
      shift 2
      ;;
    --subnet-id)
      SUBNET_ID="$2"
      shift 2
      ;;
    --availability-domain)
      AVAILABILITY_DOMAIN="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [--type local|container|oke] [--use-terraform false|true] [--tenancy OCID] [--region REGION] [--compartment OCID] [--dynamic-group NAME] [--image NAME] [--ocir-repo REPO] [--cluster NAME] [--namespace NS] [--vcn-id VCN_OCID] [--subnet-id SUBNET_OCID] [--availability-domain AD]"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Validate required vars
if [[ -z "$TENANCY_OCID" ]]; then
  echo -e "${RED}Error: --tenancy OCID is required${NC}"
  exit 1
fi
if [[ -z "$COMPARTMENT_OCID" ]]; then
  echo -e "${RED}Error: --compartment OCID is required${NC}"
  exit 1
fi
if [[ "$DEPLOY_TYPE" == "oke" && -z "$VCN_ID" ]]; then
  echo -e "${RED}Error: --vcn-id is required for OKE${NC}"
  exit 1
fi
if [[ "$DEPLOY_TYPE" == "oke" && -z "$SUBNET_ID" ]]; then
  echo -e "${RED}Error: --subnet-id is required for OKE${NC}"
  exit 1
fi
if [[ "$DEPLOY_TYPE" == "oke" && -z "$AVAILABILITY_DOMAIN" ]]; then
  echo -e "${RED}Error: --availability-domain is required for OKE${NC}"
  exit 1
fi

echo -e "${YELLOW}Deployment type: $DEPLOY_TYPE${NC}"
echo -e "${YELLOW}Use Terraform: $USE_TERRAFORM${NC}"
echo -e "${YELLOW}Tenancy OCID: $TENANCY_OCID${NC}"
echo -e "${YELLOW}Region: $REGION${NC}"
echo -e "${YELLOW}Compartment OCID: $COMPARTMENT_OCID${NC}"
echo -e "${YELLOW}Dynamic Group: $DYNAMIC_GROUP_NAME${NC}"
echo -e "${YELLOW}Auth Mode: $AUTH_MODE${NC}"

# Set OCI CLI config (uses ~/.oci/config for fallback)
# Default to instance principals for VM; OKE uses resource principals (handled in pods)
if [[ "$AUTH_MODE" == "config_file" ]]; then
  export OCI_CLI_AUTH=""
else
  export OCI_CLI_AUTH="${OCI_CLI_AUTH:-instance_principal}"
fi
export OCI_TENANCY="$TENANCY_OCID"
export OCI_REGION="$REGION"

# Function to create dynamic group
create_dynamic_group() {
  echo -e "${YELLOW}Ensuring dynamic group '$DYNAMIC_GROUP_NAME' (tenancy-level)${NC}"
  # Dynamic groups are tenancy-scoped; use TENANCY_OCID, not compartment
  local matching_rule=""
  case "$DEPLOY_TYPE" in
    local)
      # VM Instance Principals
      matching_rule="ALL {resource.type = 'instance', resource.compartment.id = '$COMPARTMENT_OCID'}"
      ;;
    container)
      # Container Instances (resource type may vary by region; use documented 'containerinstance')
      matching_rule="ALL {resource.type = 'containerinstance', resource.compartment.id = '$COMPARTMENT_OCID'}"
      ;;
    oke)
      # OKE Workload Identity uses Resource Principals per cluster; cannot know cluster OCID here.
      # Provide guidance and skip creation to avoid misconfiguration.
      echo -e "${YELLOW}Skipping dynamic group auto-create for OKE. Create a DG that targets your OKE cluster and map ServiceAccount via Workload Identity.${NC}"
      echo -e "${YELLOW}Example rule: ALL {resource.type = 'cluster', resource.compartment.id = '$COMPARTMENT_OCID'}${NC}"
      return 0
      ;;
  esac

  local dg_id=""
  set +e
  dg_id=$(oci iam dynamic-group create \
    --compartment-id "$TENANCY_OCID" \
    --name "$DYNAMIC_GROUP_NAME" \
    --matching-rule "$matching_rule" \
    --description "MCP-OCI servers access ($DEPLOY_TYPE)" \
    --query "data.id" --raw-output 2>/dev/null)
  set -e
  if [[ -z "$dg_id" ]]; then
    dg_id=$(oci iam dynamic-group list \
      --compartment-id "$TENANCY_OCID" \
      --all \
      --query "data[?name=='$DYNAMIC_GROUP_NAME'].id | [0]" --raw-output 2>/dev/null || true)
  fi
  if [[ -z "$dg_id" ]]; then
    echo -e "${RED}Dynamic group not found/created. Please create it manually in the tenancy with rule:${NC}"
    echo "$matching_rule"
    return 1
  fi
  export DYNAMIC_GROUP_ID="$dg_id"
  echo -e "${GREEN}Dynamic group ID: $DYNAMIC_GROUP_ID${NC}"
}

# Function to create IAM policies
create_policies() {
  echo -e "${YELLOW}Creating IAM policies for dynamic group (tenancy scope)${NC}"

  # Policy for compute, database, network, load balancer
  local POLICY_NAME="MCP-Policy-Compute-DB-Network"
  oci iam policy create \
    --compartment-id "$TENANCY_OCID" \
    --name "$POLICY_NAME" \
    --description "MCP servers access to compute, DB, network" \
    --statements '["Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage compute-family in tenancy", "Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage database-family in tenancy", "Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage network-family in tenancy", "Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage load-balancer-family in tenancy"]' \
    --wait-for-state SUCCEEDED 2>/dev/null || true

  # Policy for logging, monitoring
  POLICY_NAME="MCP-Policy-Observability"
  oci iam policy create \
    --compartment-id "$TENANCY_OCID" \
    --name "$POLICY_NAME" \
    --description "MCP servers access to observability services" \
    --statements '["Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage logging-family in tenancy", "Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage monitoring-family in tenancy"]' \
    --wait-for-state SUCCEEDED 2>/dev/null || true

  # Policy for cost management
  POLICY_NAME="MCP-Policy-Cost"
  oci iam policy create \
    --compartment-id "$TENANCY_OCID" \
    --name "$POLICY_NAME" \
    --description "MCP servers access to cost services" \
    --statements '["Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to use usage-api in tenancy", "Allow dynamic-group '"$DYNAMIC_GROUP_NAME"' to manage budgets in tenancy"]' \
    --wait-for-state SUCCEEDED 2>/dev/null || true

  echo -e "${GREEN}Policies created or verified${NC}"
}

# Ensure IAM (DG+policies) when using instance_principal; otherwise fall back to config_file
ensure_iam_or_fallback() {
  if [[ "$AUTH_MODE" == "config_file" ]]; then
    echo -e "${YELLOW}Auth mode 'config_file': skipping dynamic group/policies.${NC}"
    return 0
  fi
  case "$DEPLOY_TYPE" in
    local|container)
      # Try IAM setup; if not permitted, fall back to config-file auth
      if ! create_dynamic_group; then
        echo -e "${YELLOW}IAM creation not permitted or failed. Falling back to config-file auth (~/.oci/config).${NC}"
        AUTH_MODE="config_file"
        export OCI_CLI_AUTH=""
        return 0
      fi
      create_policies || true
      ;;
    oke)
      echo -e "${YELLOW}Skipping IAM auto-setup for OKE. Configure OKE Workload Identity and IAM policies manually if not present.${NC}"
      ;;
  esac
}

# Function to build and push Docker image
build_and_push() {
  echo -e "${YELLOW}Building and pushing image...${NC}"
  if [[ -z "$IMAGE_REPO" || -z "$IMAGE_TAG" ]]; then
    echo -e "${RED}IMAGE_REPO and IMAGE_TAG must be set${NC}"
    exit 1
  fi
  local IMAGE_URI="${IMAGE_REPO}:${IMAGE_TAG}"
  docker build -t "$IMAGE_URI" .
  docker push "$IMAGE_URI"
  echo -e "${GREEN}Image built and pushed: $IMAGE_URI${NC}"
}

# Function for local deployment
deploy_local() {
  echo -e "${YELLOW}Deploying locally on VM...${NC}"
  # Use local OCI config or instance principals
  export OCI_CLI_AUTH="${OCI_CLI_AUTH:-instance_principal}"
  # Bootstrap and run
  bash scripts/bootstrap.sh
  bash run-all-local.sh
  echo -e "${GREEN}Local deployment complete. Servers running locally (MCP stdio with optional /metrics).${NC}"
}

# Function for Container Instances deployment
deploy_container() {
  echo -e "${YELLOW}Deploying to OCI Container Instances...${NC}"
  echo -e "${YELLOW}Building image and pushing to OCIR...${NC}"
  build_and_push
  echo -e "${YELLOW}Creating Container Instance via OCI CLI...${NC}"
  # NOTE: Container Instances API requires a JSON payload for containers. We construct minimal JSON here.
  local IMAGE_URI="${IMAGE_REPO}:${IMAGE_TAG}"
  local CI_JSON
  CI_JSON=$(cat <<EOF
{
  "compartmentId": "$COMPARTMENT_OCID",
  "shape": "CI.Standard.E4.Flex",
  "shapeConfig": { "ocpus": 1, "memoryInGBs": 4 },
  "displayName": "mcp-oci-servers",
  "containers": [
    {
      "displayName": "mcp-oci",
      "imageUrl": "$IMAGE_URI",
      "environmentVariables": {
        "OCI_CLI_AUTH": "instance_principal",
        "OCI_REGION": "$REGION",
        "COMPARTMENT_OCID": "$COMPARTMENT_OCID"
      },
      "restartPolicy": "ALWAYS",
      "command": ["/bin/bash", "-lc", "scripts/mcp-launchers/start-mcp-server.sh all --daemon && sleep infinity"],
      "ports": [
        { "containerPort": 8000, "protocol": "TCP" },
        { "containerPort": 8001, "protocol": "TCP" },
        { "containerPort": 8002, "protocol": "TCP" },
        { "containerPort": 8003, "protocol": "TCP" },
        { "containerPort": 8004, "protocol": "TCP" },
        { "containerPort": 8005, "protocol": "TCP" },
        { "containerPort": 8006, "protocol": "TCP" },
        { "containerPort": 8007, "protocol": "TCP" },
        { "containerPort": 8008, "protocol": "TCP" },
        { "containerPort": 8009, "protocol": "TCP" },
        { "containerPort": 8010, "protocol": "TCP" }
      ]
    }
  ]
}
EOF
)
  # Create Container Instance
  local CI_ID
  set +e
  CI_ID=$(oci container-instances container-instance create --from-json "$CI_JSON" \
    --query "data.id" --raw-output 2>/dev/null)
  set -e
  if [[ -z "$CI_ID" ]]; then
    echo -e "${RED}Failed to create Container Instance. Ensure you are logged in to OCIR and have permissions.${NC}"
    echo -e "${YELLOW}Tip: docker login ${IMAGE_REPO%%/*} and ensure dynamic-group/policies allow instance principals.${NC}"
    exit 1
  fi
  echo -e "${GREEN}Container Instance ID: $CI_ID${NC}"
  oci container-instances container-instance get --container-instance-id "$CI_ID" --wait-for-state ACTIVE >/dev/null
  echo -e "${GREEN}Container Instance ACTIVE. Expose ports via VCN/NLB if needed.${NC}"
}

# Function for OKE deployment
deploy_oke() {
  if [[ "$USE_TERRAFORM" == "true" ]]; then
    echo -e "${YELLOW}Deploying OKE with Terraform...${NC}"
    cd ops/terraform
    # Init and plan
    terraform init
    terraform plan -var="tenancy_ocid=$TENANCY_OCID" -var="compartment_ocid=$COMPARTMENT_OCID" -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" -var="dynamic_group_name=$DYNAMIC_GROUP_NAME" -var="namespace=$NAMESPACE" -var="vcn_id=$VCN_ID" -var="subnet_id=$SUBNET_ID" -var="availability_domain=$AVAILABILITY_DOMAIN"
    terraform apply -auto-approve
    cd ../..
  else
    echo -e "${YELLOW}Deploying workload to existing OKE cluster...${NC}"
    # Expect KUBECONFIG already configured (via oci ce cluster create-kubeconfig or environment)
    # Apply RBAC, ConfigMap, Deployment, Service, HPA
    kubectl apply -n "$NAMESPACE" -f ops/oke/service-account.yaml
    kubectl apply -n "$NAMESPACE" -f ops/oke/configmap.yaml
    kubectl apply -n "$NAMESPACE" -f ops/oke/deployment.yaml
    kubectl apply -n "$NAMESPACE" -f ops/oke/service.yaml
    kubectl apply -n "$NAMESPACE" -f ops/oke/hpa.yaml

    # Ensure the deployment uses the pushed image (OCIR)
    if [[ -n "$IMAGE_REPO" && -n "$IMAGE_TAG" ]]; then
      echo -e "${YELLOW}Setting image on deployment to ${IMAGE_REPO}:${IMAGE_TAG}${NC}"
      kubectl set image deployment/mcp-oci-servers mcp-servers="${IMAGE_REPO}:${IMAGE_TAG}" -n "$NAMESPACE" || true
    fi

    echo -e "${YELLOW}Waiting for deployment to be ready...${NC}"
    kubectl rollout status deployment/mcp-oci-servers -n "$NAMESPACE" --timeout=300s
    echo -e "${GREEN}OKE workload deployment complete.${NC}"
  fi
}

# -------- Client connection instructions --------
print_client_instructions() {
  local mode="$1"   # local | container | oke
  local host="$2"   # hostname/IP or placeholder
  local ns="$3"     # namespace (for oke), optional

  # Port map for MCP servers (WS transport)
  local -a names=("oci-mcp-compute" "oci-mcp-db" "oci-mcp-observability" "oci-mcp-security" "oci-mcp-cost" "oci-mcp-network" "oci-mcp-blockstorage" "oci-mcp-loadbalancer" "oci-mcp-inventory" "oci-mcp-agents")
  local -a ports=(7001 7002 7003 7004 7005 7006 7007 7008 7009 7011)

  echo ""
  echo "============================"
  echo "MCP Client Connection Details"
  echo "============================"

  case "$mode" in
    local)
      echo "- Server host detected: ${host}"
      echo "- To serve over WebSocket for multi-user clients on this VM:"
      echo "    export MCP_TRANSPORT=ws MCP_HOST=0.0.0.0"
      echo "    scripts/mcp-launchers/start-mcp-server.sh all --daemon"
      echo "- Ensure your firewall/NSG allows inbound TCP to ports 7001–7011."
      echo ""
      ;;
    container)
      echo "- Container Instance created. To expose to the internet or other VCNs:"
      echo "  - Attach a Network Load Balancer (NLB) mapping ports 7001–7011 to the CI"
      echo "  - Or open Security Lists/NSGs accordingly if reachable via private networks"
      echo "- Replace <LB_OR_PRIVATE_IP> below with your reachable address."
      host="<LB_OR_PRIVATE_IP>"
      ;;
    oke)
      # Try to discover LoadBalancer address automatically
      if command -v kubectl >/dev/null 2>&1; then
        local lb_ip
        local lb_host
        lb_ip="$(kubectl get svc mcp-oci-service -n "$ns" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
        lb_host="$(kubectl get svc mcp-oci-service -n "$ns" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
        if [[ -n "$lb_ip" ]]; then
          host="$lb_ip"
        elif [[ -n "$lb_host" ]]; then
          host="$lb_host"
        fi
      fi
      echo "- OKE LoadBalancer detected host: ${host:-<PENDING>}"
      echo "- If pending, wait for EXTERNAL-IP on: kubectl get svc mcp-oci-service -n ${ns}"
      echo ""
      ;;
  esac

  echo "• Add these MCP servers to your client (example JSON for generic MCP clients that support WebSocket):"
  echo "{"
  local i
  for i in "${!names[@]}"; do
    local nm="${names[$i]}"
    local pt="${ports[$i]}"
    local comma=","
    if [[ $i -eq $((${#names[@]}-1)) ]]; then comma=""; fi
    echo "  \"${nm}\": { \"transport\": \"websocket\", \"url\": \"ws://${host}:${pt}\" }${comma}"
  done
  echo "}"

  echo ""
  echo "• For Claude Desktop (claude_desktop_config.json) or other MCP-aware clients, adapt the snippet above to their config schema."

  echo ""
  echo "• Quick test with curl (replace server/port as needed):"
  echo "  curl -v telnet://${host}:7001 || nc -vz ${host} 7001"
  echo ""
}

# Main execution
case $DEPLOY_TYPE in
  local)
    ensure_iam_or_fallback
    deploy_local
    ;;
  container)
    ensure_iam_or_fallback
    deploy_container
    ;;
  oke)
    # IAM for OKE (DG+policies) typically requires tenancy admin; we print guidance inside ensure_iam_or_fallback
    ensure_iam_or_fallback
    if [[ "$USE_TERRAFORM" == "true" ]]; then
      build_and_push
    fi
    deploy_oke
    # Print client connection details with discovered LB address if available
    print_client_instructions "oke" "<PENDING>" "$NAMESPACE"
    ;;
  *)
    echo -e "${RED}Invalid deploy type: $DEPLOY_TYPE. Use local, container, or oke.${NC}"
    exit 1
    ;;
esac

echo -e "${GREEN}Deployment successful!${NC}"
echo -e "${YELLOW}Test instance principals: oci os bucket list --auth security=instance_principal${NC}"
