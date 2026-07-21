.PHONY: smoke-sber test

PYTHON ?= python3

test:
	pytest

smoke-sber:
	@if [ ! -f pdfs/sberbank-statement.pdf ]; then \
		echo "Missing parser/pdfs/sberbank-statement.pdf"; \
		exit 0; \
	fi; \
	$(PYTHON) -m lethal_expenses.scripts.smoke_sber pdfs/sberbank-statement.pdf
