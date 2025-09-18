#!/usr/bin/env bash
set -euo pipefail

# Verification script: runs OCI CLI list calls with --debug to capture REST endpoints.
# Produces artifacts under ./verifications:
#  - compute.json / compute.debug
#  - db_systems.json / db_systems.debug
#  - adbs.json / adbs.debug
#  - summary.txt (counts + observed REST endpoints)
#
# Prereqs:
#  - OCI CLI installed and configured
#  - COMPARTMENT_OCID exported in env
#  - Optional: OCI_REGION exported in env
#
# References:
#  - OCI APIs: https://docs.cloud.oracle.com/en-us/iaas/api/
#  - OCI CLI: https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/cliconcepts.htm

if ! command -v oci >/dev/null 2>&1; then
  echo "ERROR: OCI CLI not found. See https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/cliconcepts.htm" >&2
  exit 1
fi

if [[ -z "${COMPARTMENT_OCID:-}" ]]; then
  echo "ERROR: COMPARTMENT_OCID env var is not set." >&2
  exit 1
fi

OUT="verifications"
mkdir -p "$OUT"

REGION_OPT=""
if [[ -n "${OCI_REGION:-}" ]]; then
  REGION_OPT="--region ${OCI_REGION}"
fi

echo "[verify] Running Compute/DB list calls with --debug to capture REST endpoints..."

# 1) Compute instances => GET /20160918/instances
oci ${REGION_OPT} --debug compute instance list \
  --compartment-id "${COMPARTMENT_OCID}" --all \
  > "${OUT}/compute.json" 2> "${OUT}/compute.debug" || true

# 2) DB Systems => GET /20160918/dbSystems
oci ${REGION_OPT} --debug db system list \
  --compartment-id "${COMPARTMENT_OCID}" --all \
  > "${OUT}/db_systems.json" 2> "${OUT}/db_systems.debug" || true

# 3) Autonomous Databases => GET /20160918/autonomousDatabases
oci ${REGION_OPT} --debug db autonomous-database list \
  --compartment-id "${COMPARTMENT_OCID}" --all \
  > "${OUT}/adbs.json" 2> "${OUT}/adbs.debug" || true

# Helpers
count_json() {
  local file="$1"
  python3 - "$file" <<'PY'
import json, sys
p = sys.argv[1]
try:
  with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    s = f.read()
  i = s.find('{')
  if i == -1:
    print("NA")
    raise SystemExit
  js = s[i:]
  j = js.rfind('}')
  if j != -1:
    js = js[:j+1]
  o = json.loads(js)
  data = o.get("data", [])
  if isinstance(data, list):
    print(len(data))
  else:
    print("NA")
except Exception:
  print("NA")
PY
}

endpoint_line() {
  local debug_file="$1"
  local pattern="$2"
  local expected="$3"
  # OCI CLI --debug prints Request URL lines; match the REST path segment
  local line
  line=$(grep -E "$pattern" "$debug_file" | head -n 1 || true)
  if [[ -z "$line" ]]; then
    echo "(expected ${expected}, none observed in --debug output)"
  else
    echo "$line"
  fi
}

# Build summary
{
  echo "OCI REST Verification Summary"
  echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "Region: ${OCI_REGION:-(default from config)}"
  echo

  echo "Observed REST endpoints (from CLI --debug):"
  echo "- Compute (instances):"
  endpoint_line "${OUT}/compute.debug" "/20160918/instances(\\?|$)" "GET /20160918/instances" | sed 's/^/  /' || true
  echo "- DB Systems:"
  endpoint_line "${OUT}/db_systems.debug" "/20160918/dbSystems(\\?|$)" "GET /20160918/dbSystems" | sed 's/^/  /' || true
  echo "- Autonomous Databases:"
  endpoint_line "${OUT}/adbs.debug" "/20160918/autonomousDatabases(\\?|$)" "GET /20160918/autonomousDatabases" | sed 's/^/  /' || true
  echo

  echo "Resource counts:"
  echo "  Compute instances: $(count_json "${OUT}/compute.json")"
  echo "  DB Systems:        $(count_json "${OUT}/db_systems.json")"
  echo "  Autonomous DBs:    $(count_json "${OUT}/adbs.json")"
  echo

  echo "References:"
  echo "  - OCI APIs: https://docs.cloud.oracle.com/en-us/iaas/api/"
  echo "  - Compute:   GET /20160918/instances"
  echo "  - DB:        GET /20160918/dbSystems"
  echo "  - ADB:       GET /20160918/autonomousDatabases"
  echo "  - Python SDK landing: https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/landing.html"
} > "${OUT}/summary.txt"

echo "[verify] Done. Artifacts:"
ls -1 "${OUT}"
echo
echo "[verify] Summary:"
echo "----------------------------------------"
cat "${OUT}/summary.txt"
echo "----------------------------------------"
