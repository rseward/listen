.PHONY: install run improve-text clean venv test deps test-unit test-integration test-all dev-install

.venv:
	uv venv

venv: .venv
deps: install

install:
	uv pip install -e .

dev-install: install

run:
	uv run listen

improve-text:
	@echo "Usage: echo 'text' | make improve-text"
	@echo "   or: make improve-text TEXT='your text here'"
	@if [ -n "$(TEXT)" ]; then \
		echo "$(TEXT)" | uv run improve; \
	else \
		uv run improve; \
	fi

test: test-unit

test-unit:
	uv run pytest tests/ -v -m "not integration"

test-integration:
	uv run pytest tests/ -v -m integration

test-all:
	uv run pytest tests/ -v

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf .venv
