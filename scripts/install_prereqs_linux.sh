#!/usr/bin/env bash
set -euo pipefail

# Install baseline prerequisites on a Linux host.
# - Python 3.11+, git, build tools (for python wheels), curl

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root (sudo) to install packages" >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y python3 python3-venv python3-pip git build-essential curl
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y python3 python3-venv python3-pip git gcc gcc-c++ make curl
elif command -v yum >/dev/null 2>&1; then
  yum install -y python3 python3-venv python3-pip git gcc gcc-c++ make curl
else
  echo "Unsupported package manager. Install Python 3.11+, git, and build tools manually." >&2
  exit 2
fi

echo "Prerequisites installed. Proceed with README Linux installation steps."

