.PHONY: test build lint

# Thin wrapper so `make test` (an allowlisted build entrypoint) resolves to
# the project venv's pytest without requiring PATH manipulation.
test:
	.venv/bin/python -m pytest -q tests/test_engine.py

build:
	.venv/bin/python -m compileall -q src

lint:
	.venv/bin/python -m py_compile $$(find src -name '*.py')
