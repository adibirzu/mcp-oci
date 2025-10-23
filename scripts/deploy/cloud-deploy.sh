#!/bin/bash
set -euo pipefail

# MCP-OCI Cloud Deployment Script
# Supports OCI Compute, Container Instances, and Kubernetes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOYMENT_TYPE="${1:-compute}"  # compute, container, kubernetes
REGION="${2:-eu-frankfurt-1}"
COMPARTMENT_ID="${3:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check OCI CLI
    if ! command -v oci &> /dev/null; then
        log_error "OCI CLI is not installed"
        exit 1
    fi

    # Check Terraform for compute deployment
    if [[ "$DEPLOYMENT_TYPE" == "compute" ]]; then
        if ! command -v terraform &> /dev/null; then
            log_error "Terraform is not installed"
            exit 1
        fi
    fi

    # Check kubectl for Kubernetes deployment
    if [[ "$DEPLOYMENT_TYPE" == "kubernetes" ]]; then
        if ! command -v kubectl &> /dev/null; then
            log_error "kubectl is not installed"
            exit 1
        fi
    fi

    # Validate OCI configuration
    if ! oci iam region list &> /dev/null; then
        log_error "OCI CLI is not configured properly"
        exit 1
    fi

    # Check compartment ID
    if [[ -z "$COMPARTMENT_ID" ]]; then
        log_info "Fetching compartment ID from OCI config..."
        COMPARTMENT_ID=$(oci iam compartment list --query "data[0].id" --raw-output 2>/dev/null)
        if [[ -z "$COMPARTMENT_ID" ]]; then
            log_error "Could not determine compartment ID"
            exit 1
        fi
    fi

    log_info "Prerequisites check passed"
}

# Deploy to OCI Compute Instance
deploy_compute() {
    log_info "Deploying to OCI Compute Instance..."

    cd "$PROJECT_ROOT/ops/terraform/mcp_streamable"

    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init

    # Create terraform.tfvars if it doesn't exist
    if [[ ! -f terraform.tfvars ]]; then
        log_info "Creating terraform.tfvars..."

        # Get tenancy OCID
        TENANCY_OCID=$(oci iam tenancy get --query "data.id" --raw-output)

        # Get availability domain
        AD=$(oci iam availability-domain list \
            --compartment-id "$TENANCY_OCID" \
            --query "data[0].name" \
            --raw-output)

        # Get SSH public key
        SSH_PUBLIC_KEY=""
        if [[ -f ~/.ssh/id_rsa.pub ]]; then
            SSH_PUBLIC_KEY=$(cat ~/.ssh/id_rsa.pub)
        elif [[ -f ~/.ssh/id_ed25519.pub ]]; then
            SSH_PUBLIC_KEY=$(cat ~/.ssh/id_ed25519.pub)
        fi

        cat > terraform.tfvars <<EOF
tenancy_ocid           = "$TENANCY_OCID"
compartment_ocid       = "$COMPARTMENT_ID"
region                 = "$REGION"
availability_domain    = "$AD"
ssh_public_key         = "$SSH_PUBLIC_KEY"
instance_display_name  = "mcp-oci-server"
assign_public_ip       = true
authorized_source_cidr = "0.0.0.0/0"  # Update this to restrict access
shape                  = "VM.Standard.E4.Flex"
ocpus                  = 2
memory_in_gbs          = 32
EOF
    fi

    # Apply Terraform
    log_info "Applying Terraform configuration..."
    terraform apply -auto-approve

    # Get instance IP
    INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null || echo "")
    if [[ -n "$INSTANCE_IP" ]]; then
        log_info "Instance deployed at: $INSTANCE_IP"

        # Wait for instance to be ready
        log_info "Waiting for instance to be ready..."
        for i in {1..60}; do
            if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no opc@"$INSTANCE_IP" "echo 'Instance ready'" 2>/dev/null; then
                log_info "Instance is ready!"
                break
            fi
            sleep 5
        done

        # Deploy MCP services
        log_info "Deploying MCP services to instance..."
        ssh -o StrictHostKeyChecking=no opc@"$INSTANCE_IP" <<'REMOTE_SCRIPT'
# Update system
sudo dnf update -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    sudo dnf install -y docker
    sudo systemctl enable --now docker
    sudo usermod -aG docker opc
fi

# Clone repository
if [[ ! -d ~/mcp-oci ]]; then
    git clone https://github.com/adibirzu/mcp-oci.git ~/mcp-oci
fi

# Build and run
cd ~/mcp-oci
docker build -t mcp-oci:latest .
docker run -d \
    --name mcp-oci-server \
    --restart unless-stopped \
    -p 7001-7011:7001-7011 \
    -p 8000-8011:8000-8011 \
    -p 9000:9000 \
    -p 50051:50051 \
    -e OCI_CLI_AUTH=instance_principal \
    mcp-oci:latest

echo "MCP services deployed successfully"
REMOTE_SCRIPT
    fi
}

# Deploy to OCI Container Instance
deploy_container() {
    log_info "Deploying to OCI Container Instance..."

    # Create container instance configuration
    cat > /tmp/container-instance.json <<EOF
{
    "displayName": "mcp-oci-container",
    "compartmentId": "$COMPARTMENT_ID",
    "availabilityDomain": "$(oci iam availability-domain list --compartment-id "$COMPARTMENT_ID" --query "data[0].name" --raw-output)",
    "containers": [{
        "displayName": "mcp-oci",
        "imageUrl": "ocir.$REGION.oci.customer-oci.com/mcp-oci:latest",
        "environmentVariables": {
            "OCI_CLI_AUTH": "resource_principal",
            "MCP_TRANSPORT": "streamable",
            "MCP_HOST": "0.0.0.0"
        },
        "resourceConfig": {
            "vcpusLimit": 2,
            "memoryLimitInGBs": 4
        }
    }],
    "shape": "CI.Standard.E4.Flex",
    "shapeConfig": {
        "ocpus": 2,
        "memoryInGBs": 8
    }
}
EOF

    # Create container instance
    log_info "Creating container instance..."
    CONTAINER_ID=$(oci container-instances container-instance create \
        --from-json file:///tmp/container-instance.json \
        --query "data.id" \
        --raw-output)

    log_info "Container instance created: $CONTAINER_ID"

    # Wait for container to be active
    log_info "Waiting for container to be active..."
    oci container-instances container-instance get \
        --container-instance-id "$CONTAINER_ID" \
        --wait-for-state ACTIVE \
        --max-wait-seconds 300

    # Get container IP
    CONTAINER_IP=$(oci container-instances container-instance get \
        --container-instance-id "$CONTAINER_ID" \
        --query "data.vnics[0].publicIp" \
        --raw-output)

    log_info "Container instance deployed at: $CONTAINER_IP"
}

# Deploy to OCI Kubernetes (OKE)
deploy_kubernetes() {
    log_info "Deploying to OCI Kubernetes Engine..."

    # Check if cluster exists
    CLUSTER_ID=$(oci ce cluster list \
        --compartment-id "$COMPARTMENT_ID" \
        --name "mcp-oci-cluster" \
        --query "data[0].id" \
        --raw-output 2>/dev/null || echo "")

    if [[ -z "$CLUSTER_ID" ]]; then
        log_error "OKE cluster 'mcp-oci-cluster' not found"
        log_info "Please create an OKE cluster first"
        exit 1
    fi

    # Get kubeconfig
    log_info "Getting kubeconfig..."
    oci ce cluster create-kubeconfig \
        --cluster-id "$CLUSTER_ID" \
        --file "$HOME/.kube/config" \
        --region "$REGION" \
        --token-version 2.0.0 \
        --kube-endpoint PUBLIC_ENDPOINT

    # Create Kubernetes manifests
    cat > /tmp/mcp-oci-k8s.yaml <<EOF
---
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-oci
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
  namespace: mcp-oci
data:
  OCI_CLI_AUTH: "instance_principal"
  MCP_TRANSPORT: "streamable"
  MCP_HOST: "0.0.0.0"
  COMPARTMENT_ID: "$COMPARTMENT_ID"
  REGION: "$REGION"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-oci-server
  namespace: mcp-oci
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-oci
  template:
    metadata:
      labels:
        app: mcp-oci
    spec:
      containers:
      - name: mcp-oci
        image: ocir.$REGION.oci.customer-oci.com/mcp-oci:latest
        ports:
        - containerPort: 7001
          name: compute
        - containerPort: 7002
          name: database
        - containerPort: 7003
          name: network
        - containerPort: 7004
          name: iam
        - containerPort: 7005
          name: observability
        - containerPort: 8000
          name: main
        - containerPort: 9000
          name: websocket
        - containerPort: 50051
          name: grpc
        envFrom:
        - configMapRef:
            name: mcp-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-oci-service
  namespace: mcp-oci
spec:
  type: LoadBalancer
  selector:
    app: mcp-oci
  ports:
  - port: 7001
    targetPort: 7001
    name: compute
  - port: 7002
    targetPort: 7002
    name: database
  - port: 7003
    targetPort: 7003
    name: network
  - port: 8000
    targetPort: 8000
    name: main
  - port: 9000
    targetPort: 9000
    name: websocket
  - port: 50051
    targetPort: 50051
    name: grpc
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-oci-hpa
  namespace: mcp-oci
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-oci-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF

    # Apply Kubernetes manifests
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f /tmp/mcp-oci-k8s.yaml

    # Wait for deployment
    log_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/mcp-oci-server -n mcp-oci --timeout=300s

    # Get service IP
    log_info "Waiting for LoadBalancer IP..."
    for i in {1..60}; do
        SERVICE_IP=$(kubectl get service mcp-oci-service -n mcp-oci \
            -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        if [[ -n "$SERVICE_IP" ]]; then
            log_info "Service deployed at: $SERVICE_IP"
            break
        fi
        sleep 5
    done

    # Show deployment status
    kubectl get all -n mcp-oci
}

# Create connection configuration
create_connection_config() {
    local deployment_type=$1
    local endpoint=$2

    log_info "Creating connection configuration..."

    mkdir -p "$PROJECT_ROOT/configs/connections"

    cat > "$PROJECT_ROOT/configs/connections/cloud-$deployment_type.json" <<EOF
{
    "name": "mcp-oci-cloud-$deployment_type",
    "type": "$deployment_type",
    "endpoint": "$endpoint",
    "region": "$REGION",
    "compartment_id": "$COMPARTMENT_ID",
    "connections": {
        "streamable_http": {
            "compute": "http://$endpoint:7001",
            "database": "http://$endpoint:7002",
            "network": "http://$endpoint:7003",
            "iam": "http://$endpoint:7004",
            "observability": "http://$endpoint:7005",
            "resource": "http://$endpoint:7006",
            "cost": "http://$endpoint:7007",
            "identity": "http://$endpoint:7008",
            "oneagent": "http://$endpoint:7009",
            "logging": "http://$endpoint:7010",
            "enhanced": "http://$endpoint:7011"
        },
        "websocket": "ws://$endpoint:9000",
        "grpc": "$endpoint:50051"
    },
    "auth": {
        "type": "instance_principal"
    },
    "health_check": "http://$endpoint:8000/health"
}
EOF

    log_info "Connection configuration saved to: configs/connections/cloud-$deployment_type.json"
}

# Main execution
main() {
    log_info "MCP-OCI Cloud Deployment Script"
    log_info "Deployment Type: $DEPLOYMENT_TYPE"
    log_info "Region: $REGION"

    # Check prerequisites
    check_prerequisites

    log_info "Compartment ID: $COMPARTMENT_ID"

    # Deploy based on type
    case "$DEPLOYMENT_TYPE" in
        compute)
            deploy_compute
            if [[ -n "${INSTANCE_IP:-}" ]]; then
                create_connection_config "compute" "$INSTANCE_IP"
            fi
            ;;
        container)
            deploy_container
            if [[ -n "${CONTAINER_IP:-}" ]]; then
                create_connection_config "container" "$CONTAINER_IP"
            fi
            ;;
        kubernetes)
            deploy_kubernetes
            if [[ -n "${SERVICE_IP:-}" ]]; then
                create_connection_config "kubernetes" "$SERVICE_IP"
            fi
            ;;
        *)
            log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            echo "Usage: $0 [compute|container|kubernetes] [region] [compartment_id]"
            exit 1
            ;;
    esac

    log_info "Cloud deployment complete!"
}

# Run main function
main