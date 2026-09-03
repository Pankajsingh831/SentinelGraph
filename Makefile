.PHONY: up down build logs migrate migrate-down seed simulate train evaluate test test-unit test-integration lint format clean health help

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

migrate-down:
	docker compose exec api alembic downgrade -1

seed:
	@echo "Seeding is handled automatically via Alembic migration 002_add_users_table.py. No manual seed needed."

simulate:
	docker compose run --rm -v ".:/workspace" -w /workspace -e PYTHONPATH=/workspace/apps/api:/workspace api python -m simulator.generator

train:
	docker compose run --rm -v ".:/workspace" -w /workspace -e PYTHONPATH=/workspace/apps/api:/workspace api python -m ml.training.train

evaluate:
	docker compose run --rm -v ".:/workspace" -w /workspace -e PYTHONPATH=/workspace/apps/api:/workspace api python -m ml.training.evaluate

test:
	docker compose exec api pytest

test-unit:
	docker compose exec api pytest -m unit

test-integration:
	docker compose exec api pytest -m integration

lint:
	docker compose exec api ruff check . && docker compose exec web pnpm lint

format:
	docker compose exec api ruff format . && docker compose exec web pnpm format

clean:
	docker compose down -v

health:
	curl -s http://localhost:8000/health | python -m json.tool

help:
	@echo "Available commands:"
	@echo "  up               - Start docker compose services"
	@echo "  down             - Stop docker compose services"
	@echo "  build            - Build docker compose services"
	@echo "  logs             - Follow docker compose logs"
	@echo "  migrate          - Run database migrations"
	@echo "  migrate-down     - Revert last database migration"
	@echo "  seed             - Seed database with initial data"
	@echo "  simulate         - Run simulator generator"
	@echo "  train            - Train ML model"
	@echo "  evaluate         - Evaluate ML model"
	@echo "  test             - Run tests"
	@echo "  test-unit        - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  lint             - Run linters"
	@echo "  format           - Format code"
	@echo "  clean            - Stop services and remove volumes"
	@echo "  health           - Check API health status"
