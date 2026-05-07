PYTHON ?= python

.PHONY: validate-upstreams validate-python validate-deploy-assets validate-agent-learning-proposal validate local-preflight local-up local-smoke local-debug local-down

validate-upstreams:
	$(PYTHON) scripts/validate_upstreams.py third_party/upstreams.lock.yaml
	$(PYTHON) scripts/render_import_plan.py third_party/upstreams.lock.yaml --output import-plan.json

validate-python:
	$(PYTHON) -m py_compile services/memoryd/app/*.py adapters/litellm/*.py scripts/*.py
	$(PYTHON) -m unittest discover -s services/memoryd/tests -p 'test_*.py'

validate-deploy-assets:
	$(PYTHON) scripts/validate_deploy_assets.py

validate-agent-learning-proposal:
	$(PYTHON) scripts/validate_agent_learning_proposal.py
	$(PYTHON) scripts/validate_agent_learning_proposal_generator.py

validate: validate-upstreams validate-python validate-deploy-assets

local-preflight:
	bash deploy/local/scripts/preflight-podman-m2.sh

local-up:
	bash deploy/local/scripts/bootstrap-podman-m2.sh

local-smoke:
	bash deploy/local/scripts/smoke-local.sh

local-debug:
	bash deploy/local/scripts/collect-local-debug.sh

local-down:
	bash deploy/local/scripts/down-local.sh
