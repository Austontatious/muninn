PYTHON ?= python3
MUNINN_DB_PATH ?= $(HOME)/.local/share/muninn/muninn.db

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
