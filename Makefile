.PHONY: install lint format typecheck test test-cov check clean

install:
	@uv sync
	@uv run pre-commit install

lint:
	@uv run ruff check .
	@uv run ruff format --check .

format:
	@uv run ruff check --fix .
	@uv run ruff format .

typecheck:
	@uv run ty check src/ tests/

test:
	@uv run pytest

test-cov:
	@uv run pytest --cov

check: lint typecheck test

clean:
	@uv run python -c "import pitchside, shutil; shutil.rmtree(pitchside.default_cache_dir(), ignore_errors=True)"
