#!/usr/bin/env bash
#
# Launch an OCI Compute instance prepped for MCP-OCI.
# - Creates a VM.Standard.E6.Flex instance with 2 OCPUs / 16 GB RAM.
# - Boots Oracle Linux and installs required tooling (python, git, OCI CLI).
# - Prompts for OCI environment values and drops them into /home/opc/mcp-oci/.env.
#
# Requirements:
#   * OCI CLI installed locally and configured with permissions to launch instances.
#   * An existing VCN/subnet and an SSH public key for opc user access.
#
# Usage:
#   scripts/deploy/deploy_to_oci_compute.sh

set -euo pipefail

error() {
  echo "[ERROR] $*" >&2
  exit 1
}

info() {
  echo "[INFO] $*" >&2
}

prompt_required() {
  local var_name="$1"
  local prompt_text="$2"
  local input=""
  while [[ -z "${!var_name:-}" ]]; do
    read -r -p "$prompt_text" input || true
    if [[ -n "$input" ]]; then
      eval "$var_name=\"\$input\""
    else
      echo "Value is required."
    fi
  done
}

prompt_optional() {
  local var_name="$1"
  local prompt_text="$2"
  local default_value="${3:-}"
  local input=""
  read -r -p "$prompt_text" input || true
  if [[ -n "$input" ]]; then
    eval "$var_name=\"\$input\""
  elif [[ -n "$default_value" ]]; then
    eval "$var_name=\"\$default_value\""
  fi
}

command -v oci >/dev/null 2>&1 || error "OCI CLI not found on PATH. Install it locally before running this script."

info "Gathering instance configuration..."

prompt_required COMPARTMENT_OCID "Compartment OCID: "
prompt_required SUBNET_OCID "Subnet OCID (must match desired VCN/network): "
prompt_required AVAILABILITY_DOMAIN "Availability Domain (e.g., 'kIdk:EU-FRANKFURT-1-AD-1'): "

DEFAULT_DISPLAY_NAME="mcp-oci-$(date +%Y%m%d%H%M%S)"
prompt_optional DISPLAY_NAME "Instance display name [$DEFAULT_DISPLAY_NAME]: " "$DEFAULT_DISPLAY_NAME"

DEFAULT_SSH_KEY="${HOME}/.ssh/id_rsa.pub"
prompt_optional SSH_KEY_PATH "Path to SSH public key for opc user [$DEFAULT_SSH_KEY]: " "$DEFAULT_SSH_KEY"
SSH_KEY_PATH=$(eval echo "$SSH_KEY_PATH")
[[ -f "$SSH_KEY_PATH" ]] || error "SSH public key not found at $SSH_KEY_PATH"

read -r -p "Assign public IP? [y/N]: " assign_ip_input || true
ASSIGN_PUBLIC_IP=false
if [[ "${assign_ip_input,,}" =~ ^y(es)?$ ]]; then
  ASSIGN_PUBLIC_IP=true
fi

info "Enter environment variables to place into /home/opc/mcp-oci/.env (KEY=VALUE). Press enter on an empty line to finish."
ENV_LINES=()
while true; do
  read -r env_line || true
  [[ -z "$env_line" ]] && break
  if [[ "$env_line" != *=* ]]; then
    echo "Invalid entry (expected KEY=VALUE). Try again."
    continue
  fi
  ENV_LINES+=("$env_line")
done

info "Discovering latest Oracle Linux image for VM.Standard.E6.Flex..."
IMAGE_ID="$(
  oci compute image list \
    --compartment-id "$COMPARTMENT_OCID" \
    --operating-system "Oracle Linux" \
    --operating-system-version "9" \
    --shape "VM.Standard.E6.Flex" \
    --sort-by TIMECREATED \
    --sort-order DESC \
    --query 'data[0].id' \
    --raw-output \
    --all
)"

[[ -n "$IMAGE_ID" && "$IMAGE_ID" != "null" ]] || error "Unable to locate a suitable Oracle Linux image. Verify your permissions and region."

info "Preparing cloud-init bootstrap script..."

ENV_BLOCK="# Add OCI environment values here
"
if [[ ${#ENV_LINES[@]} -gt 0 ]]; then
  ENV_BLOCK=""
  for line in "${ENV_LINES[@]}"; do
    ENV_BLOCK+="$line"$'\n'
  done
fi

USER_DATA_FILE="$(mktemp)"
METADATA_FILE="$(mktemp)"
cleanup() {
  rm -f "$USER_DATA_FILE" "$METADATA_FILE"
}
trap cleanup EXIT

cat >"$USER_DATA_FILE" <<EOF
#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/mcp-oci-firstboot.log"
exec > >(tee -a "\$LOG_FILE") 2>&1

PKG_MANAGER="dnf"
if ! command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="yum"
fi

install_packages() {
  local pkgs=(python3 python3-pip python3-virtualenv git jq unzip)
  for pkg in "\${pkgs[@]}"; do
    if ! \$PKG_MANAGER -y install "\$pkg"; then
      echo "Package \$pkg failed to install, continuing..." >&2
    fi
  done
}

install_packages

if ! command -v oci >/dev/null 2>&1; then
  curl -sSL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh -o /tmp/oci-cli-install.sh
  chmod +x /tmp/oci-cli-install.sh
  /tmp/oci-cli-install.sh --accept-all-defaults --install-dir /usr/local/lib/oci-cli --exec-dir /usr/local/bin --script-dir /usr/local/bin
  rm -f /tmp/oci-cli-install.sh
fi

install -d -m 0750 -o opc -g opc /home/opc/mcp-oci
cat <<'ENVEOF' >/home/opc/mcp-oci/.env
${ENV_BLOCK}ENVEOF
chown opc:opc /home/opc/mcp-oci/.env
chmod 600 /home/opc/mcp-oci/.env

echo "Instance provisioning complete." >&2
EOF

USER_DATA_B64="$(
  python - <<'PY'
import base64
import sys
with open(sys.argv[1], "rb") as fh:
    print(base64.b64encode(fh.read()).decode("ascii"))
PY
"$USER_DATA_FILE"
)"

printf '{"user_data":"%s"}' "$USER_DATA_B64" >"$METADATA_FILE"

info "Launching VM.Standard.E6.Flex instance..."
oci compute instance launch \
  --compartment-id "$COMPARTMENT_OCID" \
  --availability-domain "$AVAILABILITY_DOMAIN" \
  --display-name "$DISPLAY_NAME" \
  --subnet-id "$SUBNET_OCID" \
  --shape "VM.Standard.E6.Flex" \
  --shape-config '{"ocpus":2,"memoryInGBs":16}' \
  --image-id "$IMAGE_ID" \
  --assign-public-ip "$ASSIGN_PUBLIC_IP" \
  --ssh-authorized-keys-file "$SSH_KEY_PATH" \
  --metadata "file://$METADATA_FILE" \
  --wait-for-state RUNNING

info "Instance launch request submitted. Review the OCI Console for final status."
info "Once the VM is reachable, the MCP environment variables live in /home/opc/mcp-oci/.env."
