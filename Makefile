.PHONY: help install dev test lint format clean run

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Install dev dependencies"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean up cache files"
	@echo "  make run        - Run the application"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt

test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

lint:
	ruff check app tests
	mypy app

format:
	black app tests
	ruff check --fix app tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

run:
	python -m app.main
