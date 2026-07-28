ARGS = $(filter-out $@,$(MAKECMDGOALS))

.PHONY: build prod dev stop-prod stop-dev test lint lint-frontend lint-backend update export-deps alembic migrate

build:
	docker buildx bake $(ARGS)

build-dev:
	docker buildx bake $(ARGS) && ./scripts/unix/rebuild-hot-dev.sh $(ARGS)

prod:
	@trap 'docker compose down' EXIT; docker compose up $(ARGS)

dev:
	@trap './scripts/unix/stop-dev.sh' EXIT; ./scripts/unix/run-dev.sh $(ARGS)

stop-prod:
	docker compose down $(ARGS)

stop-dev:
	./scripts/unix/stop-dev.sh $(ARGS)

test:
	./scripts/unix/run-test.sh $(ARGS)

lint:
	pre-commit run --all-files $(ARGS)
	cd Node/apps/user-frontend && npm run lint && npm run build
	cd Node/apps/admin-frontend && npm run lint

lint-frontend:
	cd Node/apps/user-frontend && npm run lint && npm run build
	cd Node/apps/admin-frontend && npm run lint

lint-backend:
	pre-commit run --all-files $(ARGS)

update:
	./scripts/unix/prod-update.sh $(ARGS)

export-deps:
	./scripts/unix/export-python-dependencies.sh $(ARGS)

alembic:
	./scripts/unix/alembic-proxy.sh $(ARGS)

migrate:
	./scripts/unix/prod-db-migrate.sh $(ARGS)

%:
	@true
