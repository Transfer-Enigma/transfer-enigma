ARGS = $(filter-out $@,$(MAKECMDGOALS))

.PHONY: build prod dev stop-prod stop-dev test lint lint-frontend lint-backend update alembic migrate

build:
	docker buildx bake $(ARGS);

build-dev:
	docker buildx bake $(ARGS) && ./scripts/rebuild-hot-dev.sh $(ARGS);

prod:
	@trap 'docker compose down' EXIT; docker compose up $(ARGS);

dev:
	@trap './scripts/stop-dev.sh' EXIT; ./scripts/run-dev.sh $(ARGS);

stop-prod:
	docker compose down $(ARGS);

stop-dev:
	./scripts/stop-dev.sh $(ARGS);

test:
	./scripts/run-test.sh $(ARGS);

lint:
	uv run --active --group dev pre-commit run --all-files $(ARGS);
	cd Node/apps/user-frontend && npm run lint && npm run build;
	cd Node/apps/admin-frontend && npm run lint;

lint-frontend:
	cd Node/apps/user-frontend && npm run lint && npm run build;
	cd Node/apps/admin-frontend && npm run lint;

lint-backend:
	uv run --active --group dev pre-commit run --all-files $(ARGS);

update:
	./scripts/prod-update.sh $(ARGS);

alembic:
	./scripts/alembic-proxy.sh $(ARGS);

migrate:
	./scripts/prod-db-migrate.sh $(ARGS);

%:
	@true
