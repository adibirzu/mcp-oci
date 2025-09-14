#!/usr/bin/env bash
set -euo pipefail

# Load local overrides if present
if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

export OCI_INTEGRATION=${OCI_INTEGRATION:-1}
export TEST_OCI_PROFILE=${TEST_OCI_PROFILE:-DEFAULT}
export TEST_OCI_REGION=${TEST_OCI_REGION:-eu-frankfurt-1}

# If tenancy not set, try read from OCI config
if [ -z "${TEST_OCI_TENANCY_OCID:-}" ]; then
  # Try python3 first
  if command -v python3 >/dev/null 2>&1; then
    TEN_EXPORT=$(TEST_OCI_PROFILE="$TEST_OCI_PROFILE" python3 - <<'PY'
import os
try:
  import oci
except Exception:
  raise SystemExit(0)
profile = os.environ.get('TEST_OCI_PROFILE','DEFAULT')
cfg = oci.config.from_file(profile_name=profile)
tenancy = cfg.get('tenancy')
if tenancy:
  print(f"export TEST_OCI_TENANCY_OCID={tenancy}")
PY
    ) || true
    if [ -n "${TEN_EXPORT:-}" ]; then eval "$TEN_EXPORT"; fi
  fi
fi

if [ -z "${TEST_OCI_TENANCY_OCID:-}" ]; then
  # Fallback: parse ~/.oci/config
  CFG_FILE="$HOME/.oci/config"
  if [ -f "$CFG_FILE" ]; then
    awk -v prof="${TEST_OCI_PROFILE}" '
      $0 ~ "^\\[" prof "\\]" { inprof=1; next }
      $0 ~ /^\[/ { inprof=0 }
      inprof && $1 ~ /^tenancy/ {
        split($0,a,"="); gsub(/^[[:space:]]+|[[:space:]]+$/,"",a[2]); print a[2]; exit
      }
    ' "$CFG_FILE" > .ten.tmp || true
    if [ -s .ten.tmp ]; then
      export TEST_OCI_TENANCY_OCID="$(cat .ten.tmp)"
    fi
    rm -f .ten.tmp || true
  fi
fi

echo "Running integration tests against region ${TEST_OCI_REGION} (profile ${TEST_OCI_PROFILE})"

# Ensure virtualenv and deps are ready
if [ ! -d .venv ]; then
  make setup
fi

make test-integration
