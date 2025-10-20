#!/usr/bin/env bash
set -euo pipefail

# Simple CI docs check to ensure key sections exist and docs directory is present.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Checking README sections..."
REQUIRED=(
  "# MCP-OCI: Oracle Cloud Infrastructure MCP Servers"
  "## 🌟 Overview"
  "## 🚀 Quick Start"
  "## 🔧 Individual Server Usage"
  "## 📊 Observability"
  "### Setup Observability"
  "## 🛠️ Configuration"
  "## 🤝 Contributing"
  "## 📄 License"
)

for section in "${REQUIRED[@]}"; do
  if ! grep -qF "$section" README.md; then
    echo "Missing README section: $section" >&2
    exit 1
  fi
done

echo "Checking docs directory exists..."
test -d docs || { echo "docs/ directory not found" >&2; exit 1; }

echo "Docs checks passed."

