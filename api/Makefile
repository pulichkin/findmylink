.DEFAULT_GOAL := help
SHELL := bash

.PHONY: help check-alembic revision upgrade downgrade

ALEMBIC_CONFIG = src/configs/alembic.ini

help:
	@echo "Available commands:"
	@echo "  revision   - Create a new migration revision with autogenerate"
	@echo "  upgrade    - Upgrade database to the latest revision"
	@echo "  downgrade  - Downgrade database by one revision"

check-alembic:
	@if [ ! -f $(ALEMBIC_CONFIG) ]; then \
		echo "Error: Alembic config file not found at $(ALEMBIC_CONFIG)"; \
		exit 1; \
	fi

revision: check-alembic
	alembic -c $(ALEMBIC_CONFIG) revision -m '$(msg)' --autogenerate

upgrade: check-alembic
	alembic -c $(ALEMBIC_CONFIG) upgrade head

downgrade: check-alembic
	alembic -c $(ALEMBIC_CONFIG) downgrade -1 