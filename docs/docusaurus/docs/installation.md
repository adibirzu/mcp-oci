---
id: installation
title: Installation
---

Prereqs: Python 3.11+, OCI credentials (config file or instance principals).

Commands:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[oci]
mcp-oci doctor --profile DEFAULT --region eu-frankfurt-1
```

Next: [Configuration](configuration.md)

