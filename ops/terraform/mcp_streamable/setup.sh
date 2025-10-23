#!/usr/bin/env bash
set -euo pipefail

TF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TFVARS_JSON="${TF_DIR}/terraform.tfvars.json"
CONFIG_FILE="${OCI_CONFIG_FILE:-$HOME/.oci/config}"
PROFILE="${OCI_PROFILE:-DEFAULT}"

python_read_config() {
  python - <<'PY' "$CONFIG_FILE" "$PROFILE" "$TFVARS_JSON"
import json
import sys
from pathlib import Path
from configparser import ConfigParser

config_path = Path(sys.argv[1])
profile = sys.argv[2]
tfvars_path = Path(sys.argv[3])

def load_config():
    if not config_path.exists():
        return {}
    parser = ConfigParser()
    parser.read(config_path)
    if not parser.has_section(profile):
        return {}
    section = parser[profile]
    return {
        "tenancy_ocid": section.get("tenancy"),
        "region": section.get("region"),
    }

def load_tfvars():
    if not tfvars_path.exists():
        return {}
    try:
        with tfvars_path.open() as fh:
            return json.load(fh)
    except Exception:
        return {}

config_defaults = load_config()
tfvars_defaults = load_tfvars()
merged = {}
for key in ("tenancy_ocid", "compartment_ocid", "region", "availability_domain", "ssh_public_key", "assign_public_ip", "instance_display_name", "image_id", "authorized_source_cidr"):
    if key in tfvars_defaults:
        merged[key] = tfvars_defaults[key]
    elif key in config_defaults:
        merged[key] = config_defaults[key]
print(json.dumps(merged))
PY
}

prompt_with_default() {
  local var_name="$1"
  local prompt_text="$2"
  local default_value="${3:-}"
  local input
  if [[ -n "${default_value}" ]]; then
    read -r -p "${prompt_text} [${default_value}]: " input || true
    if [[ -z "$input" ]]; then
      input="$default_value"
    fi
  else
    while true; do
      read -r -p "${prompt_text}: " input || true
      [[ -n "$input" ]] && break
      echo "Value is required."
    done
  fi
  printf -v "$var_name" '%s' "$input"
}

defaults_json="$(python_read_config)"
TENANCY_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('tenancy_ocid',''))
PY
)"
COMPARTMENT_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('compartment_ocid',''))
PY
)"
REGION_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('region',''))
PY
)"
AD_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('availability_domain',''))
PY
)"
IMAGE_ID_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('image_id',''))
PY
)"
INSTANCE_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('instance_display_name','mcp-oci-streamable'))
PY
)"
ASSIGN_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
val=j.get('assign_public_ip', True)
print(str(val).lower())
PY
)"
SSH_KEY_DEFAULT_CONTENT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('ssh_public_key',''))
PY
)"
AUTHORIZED_SOURCE_DEFAULT="$(python - <<'PY' "$defaults_json"
import json, sys
j=json.loads(sys.argv[1]) if sys.argv[1] else {}
print(j.get('authorized_source_cidr',''))
PY
)"

DETECTED_IP="$(curl -fs https://ifconfig.me || curl -fs https://api.ipify.org || true)"
if [[ -z "$AUTHORIZED_SOURCE_DEFAULT" && -n "$DETECTED_IP" ]]; then
  AUTHORIZED_SOURCE_DEFAULT="$DETECTED_IP/32"
fi

if [[ -n "$SSH_KEY_DEFAULT_CONTENT" ]]; then
  SSH_PATH_DEFAULT=""
else
  SSH_PATH_DEFAULT="$HOME/.ssh/id_rsa.pub"
fi

prompt_with_default TENANCY_OCID "Tenancy OCID" "$TENANCY_DEFAULT"
prompt_with_default COMPARTMENT_OCID "Compartment OCID" "$COMPARTMENT_DEFAULT"
prompt_with_default REGION "Region" "$REGION_DEFAULT"
prompt_with_default AVAILABILITY_DOMAIN "Availability Domain" "$AD_DEFAULT"
prompt_with_default INSTANCE_DISPLAY_NAME "Instance display name" "$INSTANCE_DEFAULT"
IMAGE_ID="$IMAGE_ID_DEFAULT"

prompt_with_default AUTHORIZED_SOURCE_CIDR "Allowed source CIDR for MCP ports" "$AUTHORIZED_SOURCE_DEFAULT"
if [[ "$AUTHORIZED_SOURCE_CIDR" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  AUTHORIZED_SOURCE_CIDR="$AUTHORIZED_SOURCE_CIDR/32"
fi

read -r -p "Assign public IP? [true/false] [${ASSIGN_DEFAULT}]: " ASSIGN_INPUT || true
if [[ -z "$ASSIGN_INPUT" ]]; then
  ASSIGN_INPUT="$ASSIGN_DEFAULT"
fi
ASSIGN_INPUT_LOWER="$(echo "$ASSIGN_INPUT" | tr '[:upper:]' '[:lower:]')"
case "$ASSIGN_INPUT_LOWER" in
  true|t|yes|y|1)
    ASSIGN_PUBLIC_IP=true
    ;;
  false|f|no|n|0)
    ASSIGN_PUBLIC_IP=false
    ;;
  *)
    echo "Invalid entry, defaulting to true"
    ASSIGN_PUBLIC_IP=true
    ;;
 esac

if [[ -n "$SSH_KEY_DEFAULT_CONTENT" ]]; then
  read -r -p "Reuse saved SSH public key? [Y/n]: " reuse || true
  reuse_lower="$(echo "$reuse" | tr '[:upper:]' '[:lower:]')"
  if [[ "$reuse_lower" =~ ^n ]]; then
    SSH_KEY_DEFAULT_CONTENT=""
  fi
fi
if [[ -z "$SSH_KEY_DEFAULT_CONTENT" ]]; then
  prompt_with_default SSH_KEY_PATH "Path to SSH public key" "$SSH_PATH_DEFAULT"
  SSH_KEY_PATH="${SSH_KEY_PATH/#~/$HOME}"
  if [[ ! -f "$SSH_KEY_PATH" ]]; then
    echo "SSH public key not found at $SSH_KEY_PATH" >&2
    exit 1
  fi
  SSH_PUBLIC_KEY_CONTENT="$(cat "$SSH_KEY_PATH")"
else
  SSH_PUBLIC_KEY_CONTENT="$SSH_KEY_DEFAULT_CONTENT"
fi

python - <<'PY' "$TFVARS_JSON" "$TENANCY_OCID" "$COMPARTMENT_OCID" "$REGION" "$AVAILABILITY_DOMAIN" "$SSH_PUBLIC_KEY_CONTENT" "$ASSIGN_PUBLIC_IP" "$INSTANCE_DISPLAY_NAME" "$IMAGE_ID" "$AUTHORIZED_SOURCE_CIDR"
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = {
    "tenancy_ocid": sys.argv[2],
    "compartment_ocid": sys.argv[3],
    "region": sys.argv[4],
    "availability_domain": sys.argv[5],
    "ssh_public_key": sys.argv[6],
    "assign_public_ip": sys.argv[7].lower() == "true",
    "instance_display_name": sys.argv[8],
    "image_id": sys.argv[9],
    "authorized_source_cidr": sys.argv[10],
}
path.write_text(json.dumps(data, indent=2))
PY

echo "Saved configuration to ${TFVARS_JSON}"
