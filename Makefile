PY = .venv/bin/python
PIP = .venv/bin/pip
RUFF = .venv/bin/ruff
BLACK = .venv/bin/black
MYPY = .venv/bin/mypy
PYTEST = .venv/bin/pytest

.PHONY: setup dev test lint fmt

setup:
	python -m venv .venv
	$(PIP) install -U pip
	$(PIP) install -e .[dev]

dev:
	@if [ -d dev/mcp-oci-x-server ]; then \
		echo "Starting dev server..."; \
		cd dev/mcp-oci-x-server && echo "Integrate with your MCP host to run"; \
	else \
		echo "dev/mcp-oci-x-server not found. Use existing local dev server or run individual servers under src/."; \
	fi

test:
	$(PYTEST) -q

lint:
	$(RUFF) check .
	$(MYPY) src || true

fmt:
	$(RUFF) check --fix .
	$(BLACK) .
