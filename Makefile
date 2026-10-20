ARGS = $(filter-out $@,$(MAKECMDGOALS))

.PHONY: build prod dev stop-prod stop-dev test lint lint-frontend lint-backend update alembic migrate

build:
	docker buildx bake $(ARGS);

build-dev:
	docker buildx bake $(ARGS) && docker compose -f docker-compose.hot-dev.yml build $(ARGS);

prod:
	@trap 'docker compose down' EXIT;
	docker compose up $(ARGS);

dev:
	@trap './scripts/stop-dev.sh' EXIT;
	docker compose -f docker-compose.hot-dev.yml up $(ARGS);

stop-prod:
	docker compose down $(ARGS);

stop-dev:
	docker compose -f docker-compose.hot-dev.yml down $(ARGS);

test:
	docker compose -f docker-compose.test.yml run --rm test-runner $(ARGS);

lint:
	uv run --frozen --project Python --group dev pre-commit run --all-files $(ARGS);
	cd Node/apps/user-frontend && npm run lint && npm run build;
	cd Node/apps/admin-frontend && npm run lint;

lint-frontend:
	cd Node/apps/user-frontend && npm run lint && npm run build;
	cd Node/apps/admin-frontend && npm run lint;

lint-backend:
	uv run --frozen --project Python --group dev pre-commit run --all-files $(ARGS);

alembic:
	uv run --frozen --directory Python --package backend-admin alembic $(ARGS);

cli:
	uv run --frozen --directory Python --group cli python -m cli $(ARGS);

%:
	@true
