# Commandes usuelles de FreshRotten Guard (Linux / macOS ; sous Windows, voir dev.ps1).
PY := .venv/bin/python
DATASET ?= dataset

.PHONY: install dev test test-backend test-frontend test-securite lint audit cas-test calibrer robustesse

install:  ## Crée .venv et installe les dépendances backend + frontend
	test -x $(PY) || python3 -m venv .venv
	$(PY) -m pip install -q -r backend/requirements-dev.txt
	cd frontend && npm ci

dev:  ## Lance backend + frontend (BACKEND_PORT=8001 make dev si 8000 est pris)
	./dev.sh

test: test-backend test-frontend  ## Tests unitaires backend + frontend

test-backend:
	cd backend && ../$(PY) -m pytest -q --ignore=tests/securite

test-frontend:
	cd frontend && npm test

test-securite:  ## Suite de sécurité : régénère backend/artefacts/rapport_securite.{md,json}
	cd backend && ../$(PY) -m pytest -q tests/securite

lint:  ## Ruff (Python), ESLint et TypeScript (frontend)
	$(PY) -m ruff check backend scripts
	$(PY) -m ruff format --check backend scripts
	cd frontend && npx eslint . && npx tsc -b

audit:  ## Vulnérabilités connues des dépendances
	$(PY) -m pip_audit -r backend/requirements.txt
	cd frontend && npm audit --omit=dev

cas-test:  ## Cas de test sur disque + photos de démo (make cas-test DATASET=chemin/vers/dataset)
	$(PY) scripts/generer_cas_test.py --dataset $(DATASET)

calibrer:  ## Recalibre les seuils hors domaine (long)
	$(PY) scripts/calibrer_seuils.py --dataset $(DATASET)

robustesse:  ## Génère backend/artefacts/robustesse.json (tableau de bord)
	$(PY) scripts/evaluer_robustesse.py --dataset $(DATASET)
