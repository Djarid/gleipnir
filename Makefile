.PHONY: test lint build

# Test/lint run in the S-2 sandbox (bounded container), NOT on the host — see
# .gleipnir/decisions/s2-sandbox.md. These targets delegate to the sandbox
# entrypoint, which detects the container runtime, runs the full suite with
# line+branch coverage (test), and fails closed if no runtime is available.
# The old host `pytest tests/test_engine.py` target is retired: host execution
# of agent-authored test code is exactly what the sandbox removes (G-2 / T-6).

test:
	./bin/gleipnir-sandbox test

lint:
	./bin/gleipnir-sandbox lint

# `build` builds the sandbox image (operator/bootstrap). Never auto-invoked by
# test/lint — they fail closed with an instruction if the image is missing.
build:
	./bin/gleipnir-sandbox build
