# Convenience wrapper around docker compose. FLAVOR is `fast` (default) or `source`.
FLAVOR ?= fast
DC = docker compose

.PHONY: regression build notebook test test-full shell down
regression:   ## clone the regression models next to the tests (for local runs)
	test -d regression || git clone https://github.com/pmc-tools/umb-regression.git regression
build:        ## build the image locally (instead of pulling)
	$(DC) build $(FLAVOR)
notebook:     ## start Jupyter at http://localhost:8000/lab?token=umb
	$(DC) up $(FLAVOR)
test:         ## quick test suite
	$(DC) run --rm $(FLAVOR) python -m pytest tests
test-full:    ## all benchmark models
	$(DC) run --rm -e UMB_TEST_MODELS=full $(FLAVOR) python -m pytest tests
shell:
	$(DC) run --rm $(FLAVOR) bash
down:
	$(DC) down
