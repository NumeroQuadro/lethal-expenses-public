ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
WEB_DIR := $(ROOT_DIR)/web
PARSER_DIR := $(ROOT_DIR)/parser
PARSER_PDFS_DIR := $(PARSER_DIR)/pdfs
PARSER_DATA_DIR := $(PARSER_DIR)/data
DIST_DIR := $(ROOT_DIR)/dist
PARSER_BIN ?= $(ROOT_DIR)/.venv/bin/lethal-expenses
NPM ?= npm
GIT_SHA ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
ARTIFACT := $(DIST_DIR)/lethal-expenses-$(GIT_SHA).tar.gz
VITE_SOURCEMAPS ?= 0
export VITE_SOURCEMAPS

.PHONY: data web dist clean prepare-web-test-data parser-ci web-ci ci

data:
	@if [ ! -d "$(PARSER_PDFS_DIR)" ]; then 		echo "error: $(PARSER_PDFS_DIR) is missing. Add local statement PDFs before running 'make data'."; 		exit 1; 	fi
	@if ! find "$(PARSER_PDFS_DIR)" -type f -name '*.pdf' -print -quit | grep -q .; then 		echo "error: no PDF statements found under $(PARSER_PDFS_DIR). Add local PDFs before running 'make data'."; 		exit 1; 	fi
	@if [ -x "$(PARSER_BIN)" ]; then 		PATH="$(ROOT_DIR)/.venv/bin:$$PATH" lethal-expenses build; 	elif command -v lethal-expenses >/dev/null 2>&1; then 		lethal-expenses build; 	else 		echo "error: lethal-expenses CLI not found. Install it with 'python -m pip install -e parser[dev]' or activate the repo .venv first."; 		exit 1; 	fi

web:
	cd "$(WEB_DIR)" && $(NPM) ci
	cd "$(WEB_DIR)" && $(NPM) run build

dist: data web
	mkdir -p "$(DIST_DIR)"
	rm -f "$(ARTIFACT)"
	tar -C "$(WEB_DIR)/dist" -czf "$(ARTIFACT)" .
	@printf 'Created %s\n' "$(ARTIFACT)"

clean:
	rm -rf "$(WEB_DIR)/dist" "$(PARSER_DATA_DIR)" "$(DIST_DIR)"

prepare-web-test-data:
	node web/scripts/prepare-smoke-data.mjs

parser-ci:
	cd parser && PATH="../.venv/bin:$$PATH" ruff check tests src
	cd parser && PATH="../.venv/bin:$$PATH" pyright
	cd parser && PATH="../.venv/bin:$$PATH" pytest -q

web-ci: prepare-web-test-data
	cd web && npm ci
	cd web && npm run lint
	cd web && npm run test
	cd web && npx playwright install chromium
	cd web && npm run test:e2e

ci: parser-ci web-ci
