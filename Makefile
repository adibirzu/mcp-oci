PY = .venv/bin/python
PIP = .venv/bin/pip
RUFF = .venv/bin/ruff
BLACK = .venv/bin/black
MYPY = .venv/bin/mypy
PYTEST = .venv/bin/pytest

.PHONY: setup dev test lint fmt vendor-examples doctor test-integration integration-env validate-tools

setup:
	bash scripts/bootstrap.sh

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

vendor-examples:
	ORACLE_SDK_PATH?=
	@if [ -z "$$ORACLE_SDK_PATH" ]; then echo "Set ORACLE_SDK_PATH to your oci-python-sdk clone"; exit 1; fi
	bash scripts/vendor_oracle_examples.sh

doctor:
	. .venv/bin/activate && mcp-oci doctor

.PHONY: configure-claude
configure-claude:
	bash scripts/install_claude_config.sh

.PHONY: doctor-profile
doctor-profile:
	@PROFILE=${PROFILE:-DEFAULT}; REGION=${REGION:-eu-frankfurt-1}; \
	. .venv/bin/activate && mcp-oci doctor --profile $$PROFILE --region $$REGION

integration-env:
	@echo "Required env vars for direct OCI tests:"
	@echo "  export OCI_INTEGRATION=1"
	@echo "  export TEST_OCI_PROFILE=DEFAULT"
	@echo "  export TEST_OCI_REGION=eu-frankfurt-1"
	@echo "  export TEST_OCI_TENANCY_OCID=ocid1.tenancy.oc1..."
	@echo "Optional:"
	@echo "  export TEST_LOGANALYTICS_NAMESPACE=<namespace_name>"
	@echo "  export TEST_OCI_OS_BUCKET=<bucket_name>"
	@echo "  export TEST_OCI_OS_NAMESPACE=<namespace_name>"

test-integration:
	@echo "Running direct OCI integration tests..."
	@if [ -z "$$TEST_OCI_PROFILE" ] || [ -z "$$TEST_OCI_REGION" ] && [ ! -f $$HOME/.oci/config ]; then \
		echo "Missing required env vars."; \
		$(MAKE) integration-env; \
		exit 1; \
	fi
	@if [ ! -d .venv ]; then $(MAKE) setup; fi
	OCI_INTEGRATION=1 . .venv/bin/activate && pytest -q tests/integration

validate-tools:
	. .venv/bin/activate && python scripts/validate_tools.py
