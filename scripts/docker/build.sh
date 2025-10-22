#!/usr/bin/env bash
#
# Build the MCP-OCI Docker image used for running servers in containers.
# Usage:
#   scripts/docker/build.sh [--tag <image-tag>] [--no-cache]
# Environment:
#   IMAGE_NAME   Optional override for the image name (default: mcp-oci)
#   IMAGE_TAG    Optional override for the image tag  (default: latest)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

IMAGE_NAME="${IMAGE_NAME:-mcp-oci}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"

BUILD_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      IMAGE_TAG="$2"
      FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"
      shift 2
      ;;
    --no-cache)
      BUILD_ARGS+=("--no-cache")
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--tag <image-tag>] [--no-cache]" >&2
      exit 2
      ;;
  esac
done

echo "Building Docker image ${FULL_TAG}..."
docker build \
  -t "${FULL_TAG}" \
  -f Dockerfile \
  "${BUILD_ARGS[@]:-}" \
  "${ROOT_DIR}"

echo "Docker image ${FULL_TAG} built successfully."
