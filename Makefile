.PHONY: help install dev-install run test lint format clean install-uv

help:
	@echo "LOGx - AI-Powered Log Analysis"
	@echo "================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Install dependencies with uv"
	@echo "  make dev-install      - Install with dev dependencies"
	@echo "  make run              - Run the Flask application"
	@echo "  make test             - Run tests with pytest"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make lint             - Run all linters"
	@echo "  make format           - Format code with Black and isort"
	@echo "  make clean            - Remove cache and build artifacts"
	@echo "  make install-uv       - Install UV package manager"
	@echo "  make setup            - Initial project setup"
	@echo ""

install-uv:
	@echo "Installing UV package manager..."
	@powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

install:
	@echo "Installing dependencies with UV..."
	uv sync

dev-install:
	@echo "Installing with development dependencies..."
	uv sync --extra dev

run:
	@echo "Starting LOGx application on http://127.0.0.1:5000"
	python dashboard.py

test:
	@echo "Running tests..."
	uv run pytest tests/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	uv run pytest tests/ --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	@echo "Running linters..."
	@echo "Checking code style with Black..."
	uv run black --check .
	@echo "Checking imports with isort..."
	uv run isort --check-only .
	@echo "Checking code quality with flake8..."
	uv run flake8 .
	@echo "Type checking with mypy..."
	uv run mypy dashboard.py
	@echo "✅ All linters passed!"

format:
	@echo "Formatting code..."
	@echo "Running Black..."
	uv run black .
	@echo "Running isort..."
	uv run isort .
	@echo "✅ Code formatted!"

clean:
	@echo "Cleaning up..."
	@powershell -c "Get-ChildItem -Path . -Include '__pycache__' -Recurse -Force | Remove-Item -Recurse -Force"
	@powershell -c "Get-ChildItem -Path . -Include '*.pyc' -Recurse -Force | Remove-Item -Force"
	@powershell -c "Get-ChildItem -Path . -Include '.pytest_cache' -Recurse -Force | Remove-Item -Recurse -Force"
	@powershell -c "Get-ChildItem -Path . -Include '.mypy_cache' -Recurse -Force | Remove-Item -Recurse -Force"
	@powershell -c "Get-ChildItem -Path . -Include '.coverage' -Recurse -Force | Remove-Item -Force"
	@powershell -c "Get-ChildItem -Path . -Include 'htmlcov' -Recurse -Force | Remove-Item -Recurse -Force"
	@powershell -c "Get-ChildItem -Path . -Include 'dist' -Recurse -Force | Remove-Item -Recurse -Force"
	@powershell -c "Get-ChildItem -Path . -Include 'build' -Recurse -Force | Remove-Item -Recurse -Force"
	@powershell -c "Get-ChildItem -Path . -Include '*.egg-info' -Recurse -Force | Remove-Item -Recurse -Force"
	@echo "✅ Cleanup complete!"

setup: install-uv dev-install
	@echo ""
	@echo "LOGx setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy .env.example to .env"
	@echo "2. Add your HF_TOKEN to .env"
	@echo "3. Run: make run"
	@echo ""

all: format lint test
	@echo "✅ All checks passed!"

.DEFAULT_GOAL := help
