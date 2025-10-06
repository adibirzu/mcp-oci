#!/bin/bash

set -e

echo "🧹 Cleaning up MCP-OCI for Git publication"
echo "=========================================="

# Remove Python cache files
echo "🗑️  Removing Python cache files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove log files
echo "🗑️  Removing log files..."
find . -name "*.log" -delete 2>/dev/null || true

# Remove temporary files
echo "🗑️  Removing temporary files..."
find . -name "tmp_*" -delete 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true

# Remove IDE and editor files
echo "🗑️  Removing IDE/editor files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true

# Remove any actual .env files (not .env.sample or .env.example)
echo "🗑️  Removing actual .env files (keeping samples)..."
find . -name ".env" -not -name ".env.*" -delete 2>/dev/null || true

# Remove test output directories
echo "🗑️  Removing test output directories..."
rm -rf ./test-results 2>/dev/null || true
rm -rf ./coverage 2>/dev/null || true
rm -rf ./.pytest_cache 2>/dev/null || true
rm -rf ./.coverage 2>/dev/null || true

# Remove build artifacts
echo "🗑️  Removing build artifacts..."
find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove Docker/container artifacts
echo "🗑️  Removing container artifacts..."
rm -rf ./ops/pyroscope/* 2>/dev/null || true

# Remove verification files that might contain real OCIDs
echo "🗑️  Checking verification files..."
if [ -d "./verifications" ]; then
    echo "⚠️  Found verification directory - please manually review for sensitive data"
    ls -la ./verifications/
fi

# Create/update .gitignore
echo "📝 Creating/updating .gitignore..."
cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Environment files
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log
logs/

# Coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Temporary files
tmp_*
*.tmp

# OCI specific
.oci/
*.pem
*.key
wallet/
Wallet_*.zip

# Docker/Container data
ops/pyroscope/*
ops/grafana/data/*
ops/prometheus/data/*
ops/tempo/data/*

# Test results
test-results/
verification_results/

# Documentation builds
docs/_build/

# Local development
.local/
*.local

# OS generated
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
EOF

echo "✅ Cleanup completed!"
echo
echo "🔍 Manual review needed:"
echo "  1. Check ./verifications/ for sensitive data"
echo "  2. Review any remaining .json files for real OCIDs"
echo "  3. Ensure no actual credentials in any files"
echo
echo "📋 Files preserved:"
echo "  • .env.sample (template)"
echo "  • .env.example (if exists)"
echo "  • Documentation files"
echo "  • Source code"
echo
echo "🚀 Ready for Git publication!"