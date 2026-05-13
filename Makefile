PYTHON ?= python3
MUNINN_DB_PATH ?= $(HOME)/.local/share/muninn/muninn.db

.PHONY: run test eval lint init-db install enterprise-check enterprise-contracts enterprise-secrets enterprise-deps enterprise-vuln known-good

run:
	PYTHONPATH=src $(PYTHON) -m muninn.cli up --db-path "$(MUNINN_DB_PATH)"

test:
	$(PYTHON) -m pytest -q tests/test_codex_standards.py --noconftest

eval:
	$(PYTHON) evals/runner.py --check

lint:
	$(PYTHON) -m py_compile core/config.py core/prompt_loader.py core/llm.py core/trace.py tests/test_codex_standards.py evals/runner.py

.PHONY: init-db
init-db:
	@mkdir -p "$$(dirname "$(MUNINN_DB_PATH)")"
	@if [ -f "$(MUNINN_DB_PATH)" ]; then \
		echo "DB already exists at $(MUNINN_DB_PATH)"; \
	else \
		PYTHONPATH=src MUNINN_DB_PATH="$(MUNINN_DB_PATH)" $(PYTHON) scripts/init_db.py; \
	fi

.PHONY: install
install:
	@$(PYTHON) -m pip install -e .[dev]
	@$(MAKE) init-db

enterprise-contracts:
	PYTHONPATH=src $(PYTHON) -m pytest -q tests/test_cross_project_contracts.py tests/test_mcp_atlas_query.py --noconftest
	@if [ -d /mnt/data/Bifrost/src ]; then \
		PYTHONPATH=/mnt/data/Bifrost/src $(PYTHON) -m bifrost.boundary_drift --repo muninn; \
	else \
		echo "enterprise-contracts: Bifrost boundary drift checker unavailable, skipping cross-project boundary check"; \
	fi

enterprise-secrets:
	@set -e; \
	PAT='(AKIA[0-9A-Z]{16}|-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{36}|AIza[0-9A-Za-z\\-_]{35})'; \
	OUT=$$(git ls-files -z | xargs -0 -r rg -n "$$PAT" 2>/dev/null || true); \
	if [ -n "$$OUT" ]; then \
		echo "$$OUT"; \
		echo "enterprise-secrets: potential secret material detected"; \
		exit 1; \
	fi; \
	echo "enterprise-secrets: no high-confidence secret patterns found"

enterprise-deps:
	@mkdir -p artifacts/dependency
	@$(PYTHON) -m pip list --format=json > artifacts/dependency/pip-list.json || true
	@echo "enterprise-deps: wrote artifacts/dependency/pip-list.json"

enterprise-vuln:
	@if command -v pip-audit >/dev/null 2>&1; then \
		pip-audit || true; \
	else \
		echo "enterprise-vuln: pip-audit not installed; skipped"; \
	fi

enterprise-check: lint test eval enterprise-contracts enterprise-secrets
	@echo "enterprise-check: completed"

known-good: enterprise-check
	@mkdir -p artifacts/known_good
	@ts=$$(date -u +%Y%m%dT%H%M%SZ); \
	commit=$$(git rev-parse --short HEAD 2>/dev/null || echo no-commit); \
	out="artifacts/known_good/$$ts.json"; \
	printf '{\n  "timestamp_utc": "%s",\n  "commit": "%s",\n  "validation": "make enterprise-check"\n}\n' "$$ts" "$$commit" > "$$out"; \
	echo "known-good artifact: $$out"
