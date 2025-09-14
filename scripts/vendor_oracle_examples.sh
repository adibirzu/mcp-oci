#!/usr/bin/env bash
set -euo pipefail

# Vendor Oracle oci-python-sdk example scripts (showusage, showoci) into third_party/
# Usage:
#   ORACLE_SDK_PATH=/path/to/oci-python-sdk ./scripts/vendor_oracle_examples.sh

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
DEST_DIR="$ROOT_DIR/third_party/oci-python-sdk/examples"
SRC_ROOT="${ORACLE_SDK_PATH:-}"

if [[ -z "$SRC_ROOT" ]]; then
  echo "ERROR: Set ORACLE_SDK_PATH to your local oci-python-sdk clone" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
rsync -av --delete "$SRC_ROOT/examples/showusage" "$DEST_DIR/" >/dev/null
rsync -av --delete "$SRC_ROOT/examples/showoci" "$DEST_DIR/" >/dev/null

echo "Vendored examples to $DEST_DIR"
