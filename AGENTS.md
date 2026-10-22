# AGENTS.md — Project Cache for AI Agents

This file serves as a persistent cache for AI agents working on this project.
Read this first to understand conventions, structure, and constraints.

---

## Project Overview

**Transfer Enigma** — Routes calculator for rail and sea container shipping.
- Calculates shipping routes, prices, and service costs
- Supports internal database + external FESCO API as data sources
- Demo guest links for partner access: blur company names, apply profit overrides
- Demo users authenticate via `X-Demo-User-UID` header (no JWT)

---

## Project Structure

### Python Backend (`Python/`)

Three FastAPI microservices + shared libraries + CLI tools + Alembic migrations:

```
Python/
├── cli/                   # CLI debugging tools (AI-assisted route debugging)
│   ├── main.py            # click group: login, route-query, db, sheets
│   ├── auth.py            # JWT login, token storage (~/.opencode-token)
│   ├── config.py          # CLISettings: API_BASE_URL, ADMIN_API_BASE_URL, etc.
│   ├── route_query.py     # Tool 1: Query /v2/routes/calculate via API
│   ├── db_explorer.py     # Tool 2: Admin CRUD client (list, get, create, update, patch, delete)
│   └── sheets_reader.py   # Tool 3: Google Sheets reader (worksheets, show, search)
├── apps/
│   ├── shared/                # Kernel — used by every layer
│   │   ├── dto/                # Pydantic domain models
│   │   │   ├── route.py        # ContainerItem, PriceItem, ServiceItem, DropItem, RouteSegment, RouteResult
│   │   │   ├── setting.py      # SettingItem + parse_setting_value
│   │   │   ├── errors.py       # RouteError + NotFoundError, ValidationError, ResourcePermissionError
│   │   │   └── calculation.py  # CalculationRequest (the input of the calculation)
│   │   ├── orm/                # SQLAlchemy ORM models
│   │   │   ├── __init__.py     # re-exports Base, all ORM models + enums
│   │   │   ├── company.py, container.py, demo_guest.py, drop.py, point.py,
│   │   │   ├── route.py        # PriceModel, RouteModel, ServicePriceModel + RouteType, ContainerTransferTerms, ContainerShipmentTerms, ContainerOwner enums
│   │   │   ├── service.py, setting.py, cache_policy.py
│   │   ├── cache/              # The cache mechanism
│   │   │   ├── entity.py       # CacheEntity (StrEnum) — the cacheable entities
│   │   │   ├── policy.py       # CachePolicy (source, entity, enabled, ttl)
│   │   │   ├── storage.py      # CacheStorage protocol, RedisStorage, LocalStorage
│   │   │   └── backend.py      # CacheBackend — the reads and the writes
│   │   ├── concurrency/        # Locker, LocalLocker, RedisLocker
│   │   ├── identifiers.py      # SourceKind, RouteIdentifier, InternalId, ExternalId
│   │   ├── context.py          # ContextKind, CallerContext, get_context, peek_context, permissions
│   │   ├── auth.py             # require_token — the shared token check
│   │   ├── config.py           # Settings — one class for every app
│   │   ├── database.py         # Base, Database, get_database
│   │   ├── logger.py, redis_client.py, jwt_error_handler.py, domain_error_handler.py
│   ├── data/                  # Data access
│   │   ├── protocols.py        # ContainerSource, RouteSource, PointSource, DataSource + the queries + the factories
│   │   ├── sources/            # The adapters behind the protocols
│   │   │   ├── internal.py     # Our own database
│   │   │   └── fesco.py        # The FESCO API
│   │   ├── repositories/       # All the database work
│   │   │   ├── routes.py, points.py, containers.py, settings.py, demo_guests.py,
│   │   │   ├── cache_policies.py, settings_definitions.py
│   │   │   └── admin/          # The CRUD of the data browser
│   │   │       ├── crud_base.py, crud_companies.py, crud_containers.py,
│   │   │       ├── crud_drop_off.py, crud_points.py, crud_route_segments.py,
│   │   │       ├── crud_services.py, crud_settings.py, schemas.py
│   │   ├── cache/              # The cache of the sources
│   │   │   ├── registry.py     # CacheRegistry — the policies from the database
│   │   │   └── settings.py     # The cache of the settings
│   │   ├── internal/           # The internals of our own database
│   │   │   ├── aggregators/    # The queries and the transformers
│   │   │   └── query_domain/   # The declarative query builder
│   │   ├── fesco/              # The FESCO API client
│   │   │   ├── api_client/     # containers, points, routes
│   │   │   ├── cache.py        # The cache of the FESCO API
│   │   │   └── transformers/
│   │   ├── routes_loading/     # The import of the routes from the sheets
│   │   └── db_management/      # The dump, the erase and the load of the database
│   ├── services/              # Business logic
│   │   ├── route_calculation.py, points.py, profit.py, demo_transforms.py
│   │   ├── group_points.py, get_rates.py, cache_management.py
│   ├── entrypoints/           # The processes
│   │   ├── user/              # Port 8080 — the user API
│   │   │   ├── main.py, autodiscover.py, config.py
│   │   │   ├── api/v1/, api/v2/, api/v3/
│   │   │   ├── dependencies/, schemas/, utils/
│   │   ├── admin/             # Port 8082 — the admin API
│   │   │   ├── main.py, autodiscover.py, config.py, resources.py
│   │   │   ├── api/            # cache, data_browser, data_manager, demo_guests, routes_loading
│   │   │   ├── dependencies/, schemas/
│   │   └── auth/              # Port 8081 — the auth API
```

The layers may only depend on each other downwards:

```
entrypoints/  ->  services/  ->  data/  ->  shared/
```

- **`entrypoints/`** — the processes: the HTTP API of the user, the admin and the auth app. They parse the request, bind the caller context, call the services and format the answer. No business logic, no SQL.
- **`services/`** — the business logic: the use cases, the rules, the orchestration. No `fastapi`, no `sqlalchemy`; the data is reached through the protocols of the data layer.
- **`data/`** — the access to the data: the repositories (they own their session), the query builder, the source adapters behind the protocols, the cache of the sources.
- **`shared/`** — the kernel: the domain models, the ORM models, the cache mechanism, the identifiers, the caller context, the database, the config.

The rules are checked by `Python/tests/test_architecture.py` — a violation of a layer fails the test suite.

### Node Frontends (`Node/apps/`)

```
Node/apps/
├── user-frontend/        # Vue 3 + Vite — Main user calculator UI
│   └── src/
│       ├── pages/        # CalculatorPage, LoginPage, Error404Page
│       ├── components/   # Reusable Vue components
│       ├── composables/  # Vue composables (useBlurredFields, etc.)
│       ├── stores/       # Pinia stores (user, router, lang, points, rates, routes)
│       ├── services/     # Business logic (auth, calculator, rates, points, etc.)
│       ├── api_helpers/  # API fetch wrappers (user, routes, points, rates)
│       ├── helpers/      # requests.ts (fetchAsJSON wrapper with demo headers)
│       ├── interfaces/   # TypeScript interfaces
│       └── providers/    # Auth provider
├── admin-frontend/       # React 19 + Vite — Admin dashboard
│   └── src/
│       ├── pages/        # Login, Dashboard, DataImport, DemoGuests, Settings
│       ├── api/          # Axios API clients (Auth, Data, DemoGuests, Settings)
│       ├── services/     # Auth service
│       ├── widgets/      # Sidebar, LoginForm
│       ├── layouts/      # MainLayout, EmptyLayout
│       └── interfaces/   # TypeScript interfaces
└── old-user-frontend/    # Legacy vanilla JS frontend (reference only)
```

### Config & Infrastructure

```
config/
├── nginx/conf/           # Nginx templates (production + dev)
├── database/             # SQL dumps, dev DB init, backup volumes
└── ...

scripts/                  # Dev workflow scripts (run, stop, rebuild, migrate)
```

### Build

**Package Manager:** uv (`Python/pyproject.toml` + `Python/uv.lock`). Always use `uv add` CLI, don't edit dependencies manually.

**Dependency groups** (PEP 735):
| Group | Contents |
|-------|----------|
| `[project] dependencies` | Runtime deps (installed in all images) |
| `[dependency-groups] dev` | Linting/pre-commit tools (black, pre-commit, ipython) |
| `[dependency-groups] tests` | Test frameworks (pytest, pytest-asyncio, httpx, aiosqlite) |

`uv.lock` is the single source of truth — committed to git, consumed via `uv sync --frozen` in Docker. No exported `.txt` files.

**Updating dependencies:** from `Python/` use `uv lock --upgrade-package <name>` (re-locks only that package, keeps everything else pinned) or `uv lock --upgrade` (everything). `uv add <name>` / `uv remove <name>` for changing the declared set. `poetry` is gone — do not use `poetry lock`/`poetry export`, and do not re-create `requirements*.txt`.

**Dockerfile stages** (`Python/Dockerfile`, multistage):
| Stage | Base | Purpose |
|-------|------|---------|
| `uv` | `ghcr.io/astral-sh/uv:0.13.3` | Binary-only source image (no Python/shell) — only `/uv` + `/uvx` are copied from it. **Pin the version** when updating. |
| `python-base` | `python:3.14-slim` | Common runtime base: user setup, `WORKDIR`, `USER appuser`. No uv, no `UV_*` env. |
| `builder` | `python-base` | Copies `/uv`+`/uvx` (build-time only), sets `UV_*` env, `uv sync --frozen --no-dev` → prod `.venv` |
| `builder-tests` | `builder` | `uv sync --frozen --group tests` → prod+tests `.venv` (inherits uv from `builder`) |
| `python-apps` | `python-base` | Copies prod `.venv` from `builder`, runs FastAPI via uvicorn |
| `db-migration` | `python-base` | Copies prod `.venv` from `builder`, runs Alembic migrations |
| `test-runner` | `python-base` | Copies prod+tests `.venv` from `builder-tests`, runs pytest |

`uv`/`uvx` and the `UV_COMPILE_BYTECODE`/`UV_LINK_MODE`/`UV_PYTHON` env vars exist **only in `builder`/`builder-tests`** — they are build-time tools. Runtime stages (`python-apps`, `db-migration`, `test-runner`) derive from `python-base` and must NOT contain uv (saves ~42 MB per runtime image).

The `test-runner` stage copies `apps/` to `/workspace/apps/`, `tests/` to `/workspace/tests/`, and uses hardcoded `/workspace` paths in CMD (JSON exec form, no `ENV`/shell expansion needed). `APP_DIR` is a build-time `ARG` only (default `/workspace`), never used at runtime.

### Redis Caching

**Status:** Active — Redis service available in all environments (prod, dev, test).

**Redis client:** `shared/redis_client.py` — async singleton via `get_redis()` / `get_redis_client()`. Connection pool managed by `redis.asyncio`.
- `decode_responses=True` — all values are strings (JSON serialized)
- Config: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` from `shared/config.py`

**One mechanism, per-source configuration.** The cache is driven by the `cache_policies` table — one row per `(source, entity)` with the switch and the TTL. An entity **without** an enabled policy row is not cached at all.

| Piece | Location | Content |
|-------|----------|---------|
| `CacheEntity` | `shared/cache/entity.py` | `StrEnum` of the cacheable entities — a policy cannot reference an unknown one |
| `CachePolicy` | `shared/cache/policy.py` | `source`, `entity`, `enabled`, `ttl` |
| `CacheStorage` | `shared/cache/storage.py` | `Protocol`; `RedisStorage` and `LocalStorage` (in process, for the tests) |
| `CacheBackend` | `shared/cache/backend.py` | the reads and the writes over a `CacheStorage` |
| `CacheRegistry` | `data/cache/registry.py` | the policies from the database, one backend per source |
| `CachePolicyModel` | `shared/orm/cache_policy.py` | the ORM model of the table |

**`CacheBackend`:**
- `get(entity, *parts, model?, many=True)` — read, validate against the model, `None` when the entity is not cached
- `set(entity, *parts, data, ttl?, dump=False)` — write, `False` when the entity is not cached
- `set_async(...)` / `silent_set_async(...)` — fire-and-forget write, guarded by `LocalLocker` **by the cache key**
- `delete(entity, *parts)`, `flush()`, `keys(entity?)` — the administration of the cache

**Cache key scheme** — `{source}:{entity}:{parts}`:

| Data | Key pattern | TTL | Eviction |
|------|-------------|-----|----------|
| Currency rates | `cbr:rates:latest` | from the policy | volatile-lru |
| FESCO departures | `fesco:departures:{date}` | from the policy | volatile-lru |
| FESCO destinations | `fesco:destinations:{date}:{dep_id}` | from the policy | volatile-lru |
| FESCO containers | `fesco:containers:{date}:{dep}:{dest}` | from the policy | volatile-lru |
| FESCO routes | `fesco:routes:{date}:{dep}:{dest}:{wte_ids}` | from the policy | volatile-lru |
| Settings | `internal:settings:{group}:{name}` | from the policy | volatile-lru |

The TTL of the points of the FESCO API depends on the date (24h for today, 12h for the other days) and is passed as an override, the policy gives the default one.

**The cache is loaded on startup:** the lifespans of the user and the admin apps call `await get_cache_registry().load()` after the database and the Redis are ready. The policies are read from the database, so an entity is cached only after its row exists.

**The rows are created by hand after the deploy** — there is no automatic seeding. Until they exist, nothing is cached:

```sql
INSERT INTO cache_policies (source, entity, enabled, ttl) VALUES
  ('internal', 'settings',    1, 43200),
  ('cbr',      'rates',       1, 43200),
  ('fesco',    'departures',  1, 43200),
  ('fesco',    'destinations',1, 43200),
  ('fesco',    'containers',  1, 86400),
  ('fesco',    'routes',      1, 43200);
```

**The admin panel manages the cache:** `GET /admin/api/cache` (the sources and their policies), `GET /admin/api/cache/{source}` (the keys), `PATCH /admin/api/cache/{source}/{entity}` (the switch and the TTL), `DELETE /admin/api/cache/{source}` (flush it).

**The settings cache — transparent:** `data/cache/settings.py` implements cache-aside for the DB backed settings:
- `get_setting_cached(group, name, *, session=None)` — the cache → the database → a fire-and-forget write
- `set_settings_cache(item)` — write a single setting
- `delete_settings_cache(group, name)` — remove a single setting
- `ensure_settings()` — the seeding of the settings, called by the lifespan of the user app
- The admin CRUD of the settings updates the cache after the write, so the cache stays in sync

**The rates cache** (`services/get_rates.py`), it uses the same mechanism under the source `cbr`:
1. Always try the CBR API first (`ExchangeRates`)
2. On success: return `(rates, today)` + a background write through the `CacheBackend` (`CacheEntity.RATES`)
3. On failure: fallback to the cache — return `(rates, cached_date)` from the cache
4. If both fail: `RuntimeError`

**API endpoints:**
- `GET /v1/rates` — returns `{USD: 90.0, ...}` (rates only, async now)
- `GET /v2/rates` — returns `{rates: {...}, updated_at: "2026-06-16"}` (adds date)

**Redis docker-compose:**
- `docker-compose.yml`: `valkey/valkey:alpine`, AOF+RDB persistence, `volatile-lru` (512mb maxmemory)
- `docker-compose.hot-dev.backend.yml`: extends redis from base
- `docker-compose.test.yml`: redis with 128mb maxmemory, `test` profile

### Locker System

`shared/concurrency/` — lock/unlock abstraction for preventing duplicate concurrent operations:

- **`Locker` (ABC)** — sync/async `acquire`/`release`, context managers, class-level `@locked`/`@alocked` decorators that wrap functions with acquire/release semantics
- **`LocalLocker`** — in-process threading-based lock (`threading.Lock` + `dict[str, bool]`). Used by `CacheBackend.set_async` to prevent duplicate fire-and-forget writes for the same cache key
- **`RedisLocker`** — distributed Redis-based lock using `SET NX EX` (async only; sync methods raise `RuntimeError`)
- **`TaskAlreadyRunningError`** — raised on re-acquire

The `@locked` decorator takes the key from the **first positional argument** of the wrapped function. On a method that is the instance, so the key function must build it explicitly: `@LocalLocker.locked(key=lambda self, entity, *parts, **__: self.key(entity, *parts))`.

### Nginx Routing

| Location | Proxy Target | Purpose |
|----------|-------------|---------|
| `/api/user/` | `auth:8081` | Auth endpoints (login, refresh, me) |
| `/api/` | `calculator:8080` | User API (routes, points, rates, demo) |
| `/admin/api/` | `backadmin:8082` | Admin API (data import, demo guests) |
| `/admin` | Admin frontend static | Admin UI |
| `/` | User frontend | Main calculator UI |

---

## Commit Rules

### Structure
1. **One commit = one micro-feature.** Never mix unrelated features in one commit.
2. **Each commit must produce working code.** All imports must resolve, all called functions must exist. If a commit would be too large, split into smaller commits by module — but each intermediate commit must be functional.
3. **Keep history linear — no fix commits on top.** If the current branch contains a commit with a bug or lint issue, amend that commit via rebase rather than creating a separate fix commit. This keeps history clean and avoids fixup noise.

### Commit Message Format
```
<Module>: <Description in English>
```
Examples:
- `Auth Backend: Add demo guest login by UID`
- `User Frontend: Add blurred company display for demo guests`
- `Python: Add feature flags module`
- `Database: Add demo_guests table`
- `Nginx: Add SSL support`

Module prefixes:
- `Auth Backend:` — `entrypoints/auth` only
- `User Backend:` — `entrypoints/user` only
- `Admin Backend:` — `entrypoints/admin` only
- `Python:` — crosses multiple Python modules (e.g., adding shared code)
- `User Frontend:` — Vue app only
- `Admin Frontend:` — React app only
- `Database:` — Alembic migrations, SQL scripts
- `Nginx:` — Nginx config changes
- `Docs:` — Documentation only
- `CI:` — CI/CD workflow changes

### Pre-Commit Checks
- Before each Python commit: `make lint-backend` — this catches lint/type errors early, avoiding fix commits on top
- Before each Node commit: `make lint-frontend`
- Fix any lint/type errors before committing

### CI Workflows
- `project-lint.yml` — pre-commit + ESLint, runs on every PR
- `project-tests.yml` — pytest (SQLite in-memory), runs on PR, push to main/master, and manual
- `project-build.yml` — Docker Bake build + optional deploy, manual trigger only
- `project-deploy.yml` — SSH deploy, reusable sub-workflow

---

## Code Style & Conventions

### General
- **All code comments must be in English.**
- **All commit messages must be in English.**
- **Maximize code reuse.** Before writing new code, check if existing utilities/modules can be extended. Duplication should be justified.
- Follow existing patterns in the codebase. Don't introduce new libraries or patterns unless necessary.

### Python
- Uses `async`/`await` throughout (FastAPI + SQLAlchemy async)
- Type annotations required (`flake8` + `mypy` enforce this)
- Imports sorted with `isort`
    - pre-commit hook repo: `https://github.com/PyCQA/isort` (rev `9.0.2`) — **not** `pre-commit/mirrors-isort`, which is frozen at `v5.10.1`
    - isort derives valid `py_version` targets from its `isort/stdlibs/py3XX.py` tables; 5.10.1 tops out at `310`, py314 support appeared in `7.0.0`. Bump the rev together with `py_version` in `Python/pyproject.toml` `[tool.isort]`
- Max line length: 120 chars
- Max McCabe complexity: 10
- Existing flake8 plugins: `flake8-builtins`, `flake8-comprehensions`, `flake8-eradicate`, `flake8-expression-complexity`, `flake8-simplify`, `flake8-bugbear`, `flake8-pie`, `flake8-print`, `flake8-noqa`, `flake8-broken-line`
- Router auto-discovery pattern: place `router = APIRouter(...)` in any module under `api/` — it gets discovered automatically
- DB sessions: use `async with db.session_context() as session` — auto-commits on exit, auto-rollbacks on exception
- Alembic migrations: placed in `Python/alembic/versions/`, excluded from pre-commit (`exclude: 'Python/alembic/.*'`)

### Python Tests
- Tests live in `Python/tests/`, run with `make test`
    - `test_architecture.py` — the rules of the layers (see the dependencies graph above)
    - `test_route_calculation.py` — route calculation (service-level: internal, FESCO, mixed, errors; handler-level: format conversion, demo transforms/strip/profit) and the search of the containers
    - `test_internal_aggregators.py` — containers, paths (rail/sea/COC/SOC/expired/services/drop/dropp_off/no_data/process_results), hide-sea-soc + route-type feature flags + TRUCK routes (direct, truck→rail, rail→truck, truck→rail→truck, truck→sea→rail→truck, truck→rail→sea→truck, sea+rail with truck, base queries for "without delivery" button)
    - `test_deduplication.py` — the routes with the same segments are returned once (the rule lives in the service)
    - `test_profit.py` — currency conversion, profit application, segment type filtering, mixed segments, currency conversion in profit
    - `test_auth_utils.py` — `strip_demo_fields`, `get_caller_context` with/without/invalid demo header, empty routes
    - `test_get_points.py` — `get_departure_points`, `get_destination_points`, no routes, multiple companies
    - `test_demo_guest_repo.py` — `get_demo_guest_by_uid` found/not found/profit overrides, `list_demo_guests` empty/multiple
    - `test_get_rates.py` — `get_rates` returns dict, caching through the `CacheBackend`, with datetime, API failure fallback, the entity that has no policy
    - `test_setting_cache.py` — `get_setting_cached` cache hit/miss/not_found, and the entity that has no policy is not cached
    - `test_fesco_api_client.py` — FESCO API transformations, container search, points, routes, caching
    - `test_deduplication.py` — route deduplication preserves distinct routes, multiple prices
    - `test_route_calculation_v3_sse.py` — SSE streaming, demo transforms, error handling
    - `test_context.py` — the caller context: `get_context` raises without a bound context, `permissions` allows the admin and rejects the others
    - `test_identifiers.py` — the ids of a source: equality by hash, the source kind, the canonical form
    - `test_query_domain_expr.py` — ColumnRef, Condition, Connector
    - `test_query_domain_builder.py` — RouteBuilder API tests + DB-backed build tests
    - `test_resources_base_path.py` — the resources of the apps are found from the base path
    - `admin/data_sync/` — the admin data browser and the data manager
- **Test DB**: SQLite in-memory (`sqlite+aiosqlite`). Tables created via `Base.metadata.create_all()`, **not** via Alembic migrations (migrations have MySQL-specific code).
- **Auth mocks**: patch `get_demo_guest_by_uid`, `get_database`, and `request_auth` directly
- **FESCO API mocks**: use `unittest.mock.patch` on `data.fesco.api_client` directly
- **The caller context**: the `caller_context` fixture binds a `CallerContext` for the duration of a test and restores it after
- **Test data**: factory functions in `Python/tests/factories.py` build ORM objects with sensible defaults
- **Currency rates**: tests use RUB-relative rates `{"USD": 90.0, "RUB": 1.0}`; `_convert_currency` formula is `amount * rates[from] / rates[to]`
- Run: `make test` (Docker, profile `test` — won't start with plain `docker compose up`)

### Python Module Dependencies Graph
```
entrypoints ─── services ─── data ─── shared
```

The layers may only depend on each other downwards. `Python/tests/test_architecture.py` checks it:

| Rule | Check |
|------|-------|
| The services do not import the web framework or the ORM | `test_services_do_not_import_the_web_framework_or_the_orm` |
| The services reach the data through the protocols | `test_services_reach_the_data_through_the_protocols` |
| The data layer does not import the layers above it | `test_data_does_not_import_the_layers_above` |
| The entrypoints do not import a concrete source | `test_entrypoints_do_not_import_a_concrete_source` |
| No private symbol crosses a package | `test_no_private_symbol_is_imported_across_the_packages` |

The private symbol rule is checked **per package** (not per layer): the package of an imported module is resolved from the file system, so `data.cache` and `data.protocols` are two different packages.

### The Caller Context
One global context instead of the context passed through every signature — `shared/context.py`:

- **`ContextKind`** — `SYSTEM` (a process, e.g. a scheduler), `ADMIN`, `DEMO`, `USER` (reserved for a future users and roles system)
- **`CallerContext`** — the kind, the identity, the pricing overrides, the fields the caller must not see, the user id and the permissions
- **`get_context()`** — the context of the current call; it **raises** when nothing is bound, so a use case never runs with the privileges of nobody by accident
- **`peek_context()`** — the context of the current call, or `None` when nothing is bound
- **`set_context()` / `reset_context()`** — bind and restore, over a `contextvars.ContextVar` (per task, so the requests do not see each other)
- **`@permissions(ContextKind...)`** — a decorator that checks the kind of the caller; it is used **only in the `data/` layer**, on the operations that mutate the data or that are admin only. The services are not decorated — the user facing use cases are public

The entrypoints bind the context: the user app resolves it from the request (JWT → `ADMIN`, `X-Demo-User-UID` → `DEMO`), the admin app binds `ADMIN`, a process binds `SYSTEM` explicitly. The services read it with `get_context()`.

The services never take the context as an argument — that is what makes them reusable by a process that is not an HTTP request.

### TypeScript / Frontends
- **User Frontend**: Vue 3 Composition API (`<script setup lang="ts">`), Pinia stores, Vue Router
- **Admin Frontend**: React 19 functional components, React Router, Axios for API
- Both use TypeScript, Bootstrap 5

---

## Workflow Rules

### No Direct Merge
- **All merges must go through Pull Requests.** No `git merge` on main/protected branches.
- Rebasing is preferred for feature branches (clean history).

### Branching
- Feature branches: `feature/<short-description>`
- Bugfix branches: `fix/<short-description>`
- Keep branches up to date with the target branch via rebase, not merge.

### Always run linting before committing
- Python: `make lint-backend`
- Frontends: `make lint-frontend`
- Both: `make lint`

---

## Architecture & Design Decisions

### API Versioning
- User API uses URL versioning: `/v1/`, `/v2/`, `/v3/`
- Auth and Admin APIs are not versioned
- `/v3/routes/calculate` (POST) is an SSE endpoint for progressive route streaming — each route/error is yielded as an SSE event when available

### Auth Flow
1. Login sets JWT access + refresh cookies (httpOnly)
2. Frontend refreshes token on interval via `POST /token/refresh`
3. Demo users authenticate via `X-Demo-User-UID` header (no JWT, the auth app is NOT involved)

### Demo Guest Feature
- Admin creates demo guests with UID + profit overrides (stored in `demo_guests` table)
- Demo link format: `/demo/<UID>`
- All demo auth is in the user entrypoint — the auth app is NOT involved
- Backend: the `bind_caller_context` dependency checks the `X-Demo-User-UID` header → looks up the `demo_guests` table → builds a `CallerContext` (kind `DEMO`, the profit overrides, the blurred fields). If no header, it falls through to the JWT via `request_auth` and binds `ADMIN`.
- **An unknown demo UID also falls back to `ADMIN`** (the lookup returns nothing → the context is built as `ADMIN`), so a mistyped UID is not a demo guest and the caller is not blurred
- The endpoints use `Depends(bind_caller_context)` (it supports both the JWT and the header)
- Demo endpoints: `POST /api/v2/demo/validate` (validates UID), `GET /api/v2/demo/feature-flags` (returns blurred_fields list)
- Frontend: `helpers/requests.ts` → `demoHeaders()` reads `useDemoAuth()` Pinia store → injects `X-Demo-User-UID` into every `fetchAsJSON()` call
- Demo users see blurred company names via CSS class (driven by `useBlurredFields` composable ← `featureFlags` store)
- Profits (`sea_profit`, `rail_profit`) are added to route prices for demo users only (in the profit service, it reads the caller context)
- `Error404Page.vue` shown for invalid UIDs or unmatched routes

### Pinia Timing Constraints (Critical!)
- `useStore()` (Pinia) calls `inject(piniaSymbol)` → requires `getCurrentInstance()` (Vue component context)
- **CANNOT use Pinia in route `beforeEnter` guards** — no component context (`getCurrentInstance()` is null). Use plain `fetch()` + try/catch.
- **CAN use Pinia in `<script setup>` top level** — `currentInstance` is set during setup
- **`onMounted` fires children-first in Vue 3** — parent's `onMounted` fires AFTER children's. If demoUid must be set before child API calls, set it at `<script setup>` level.
- `fetchAsJSON()` reads `useDemoAuth()` synchronously before `await`. Works if called from component context (setup, lifecycle, event handler).

### Feature Flags Flow
- `/demo/feature-flags` is fetched **independently of route** — driven by `demoUid` state
- `providers/auth.ts` watches `useDemoAuth().demoUid` → fetches with/without `X-Demo-User-UID` header → sets `useFeatureFlags().blurredFields`
- `immediate: true` ensures correct state on initial load
- Feature flags are **not cleared explicitly** — the watcher auto-updates when `demoUid` changes (clearing demoUid → fetch without header → empty blurred_fields)

### Source Contract

**`data/protocols.py`** — the contract between the services and the data:
- `ContainerQuery`, `RouteQuery` — the input of a query (a date, a departure, a destination, the containers)
- `ContainerSource`, `RouteSource`, `PointSource` — the protocols a source implements
- `DataSource` — all three at once, the type of the factories
- `get_internal_source()` / `get_fesco_source()` — the factories; the adapter is imported **inside** the function, so the protocols and the adapters do not import each other in a cycle

**The services never import a concrete source.** They call the factories of `data.protocols` and work with the protocol, the adapters live in `data/sources/`:
- `data/sources/internal.py` — `InternalSource` — our own database
- `data/sources/fesco.py` — `FescoSource` — the FESCO API

The guard test checks this rule: `data.sources` and `data.repositories` are forbidden in the services.

### Domain Models

**`shared/dto/route.py`** — Route entities (Pydantic V2 `BaseModel`):
- Models: `ContainerItem`, `PriceItem`, `OnePrice`, `ServiceItem`, `DropItem`, `RouteSegment`, `RouteResult`
- `OnePrice` represents FESCO single-price format with `beginCond`/`finishCond` (price-level conditions, set only for sea segments)
- `PriceItem` represents internal multi-price format (always has `value: float`)
- `RouteSegment.prices` can be `list[PriceItem]` (internal) or `OnePrice` (FESCO) or `None`

**`shared/dto/setting.py`** — Setting entities (Pydantic V2 `BaseModel`):
- `SettingItem(id, group, name, description?, value_type, value)` — unified settings model
- `value: bool | int | float | str | dict | list | None` — auto-converted from DB string via `_parse_value` validator (`mode="before"`):
    - `INT` → `int(v)`, `FLOAT` → `float(v)`, `BOOL` → `v.lower() in ("true", "1")`, `JSON` → `json.loads(v)`
- `locked: bool = False` — prevents rename, type change, and deletion (CRUD enforcement)
- `from_model(model: SettingModel) -> SettingItem` — factory from ORM model
- `parse_setting_value(value, value_type)` — standalone function used by both `_parse_value` and admin CRUD validation

**`shared/dto/errors.py`** — Error model and the domain errors:
- `RouteError(error_type: str, error_text: str, source: str | None)`
- Used in services (no source) and points handlers (`"internal"`/`"external"`)
- `NotFoundError` — the entity was not found
- `ValidationError` — the input data failed validation
- `ResourcePermissionError(PermissionError)` — the caller is not allowed to perform the operation

**`shared/dto/calculation.py`** — `CalculationRequest` — the input of the calculation service. The API model of the request (`CalculateFormRequest`) turns itself into it with `to_calculation_request()`, so the services do not depend on the shape of the API.

**`shared/identifiers.py`** — the ids of the entities of a source:
- `SourceKind` — `INTERNAL`, `EXTERNAL`
- `RouteIdentifier` (ABC) — `source` (read only), `__str__` (the canonical form, used for the cache keys), `__hash__`, `__eq__` (by the hash, so the ids are comparable and usable as dict and set members)
- `InternalId` (an int) and `ExternalId` (a str) — the adapters convert at the boundary

### Service/API Separation (Single Responsibility)
- **Services** (`services/`) hold the business logic: the use cases, the rules, the orchestration
- **API handlers** (`entrypoints/*/api/`) parse the request, bind the caller context, call the service and format the answer
- The models in `shared/dto/route.py` are Pydantic V2 `BaseModel` (not dataclasses) — they serve as both domain objects and response schemas
- `calculate_routes()` returns `tuple[list[RouteResult], list[RouteError]]` (raw Pydantic models + errors)
- The V2 handler (`entrypoints/user/api/v2/routes/post.py`) owns `_normalize_routes` — the tuple format of the response
- The demo rules are one service (`services/demo_transforms.py`), it reads the caller context
- No duplicate Pydantic response models — the schemas of the entrypoints import `RouteSegment`, `DropItem`, `ServiceItem` from `shared.dto.route`

### Database
- MariaDB, accessed via SQLAlchemy async + `aiomysql`
- Migrations via Alembic
- All ORM models and enums defined in `shared/orm/`
- Both use the same `Base` class from `shared.database`
- The repositories own their session: `async with get_database().session_context() as session` — auto-commits on exit, auto-rollbacks on exception

### Route Calculation — Key Logic

> Подробное описание логики расчёта маршрутов см. в [ROUTES-CALCULATION-LOGIC.md](./ROUTES-CALCULATION-LOGIC.md).

** Query Composer (`data/internal/query_domain/`) —** wired into `data/repositories/routes.py` (replaced raw SQL `build_usual_query`/`build_base_sea_rail_query`). Full API docs in [`query_domain/README.md`](./Python/apps/data/internal/query_domain/README.md).
- **`ColumnRef`** — single entity for column references (no separate `Field`/`RelField`). Accessed via `Segment.__getattr__`/`DropOff.__getattr__` which looks up `_COLUMN_MAP` (domain → DB column name). Methods: `.equals()`, `.not_equals()`, `.not_()`, `.not_null()`, `.null()`, `.in_()`, `.lte()`, `.gte()`. `_id` columns hidden (only accessible via relationship names like `company` → `company_id`).
- **`Condition`** — AST node: `op`, `left`, `right`, `operand`, `operands`. Supports unary (not/not_null/null), binary (eq/in/lte/gte), and n-ary (and/or) operations.
- **`Segment`** — represents a route table segment. `type` param accepts string or `RouteType` enum (auto-converts). `auto_services=False` default. All route columns accessible via `_COLUMN_MAP`.
- **`DropOff`** — represents a drop_off table row. `exists()` returns `id.not_null()`.
- **`RouteBuilder`** — fluent API: setters (`set_containers`, `set_start_point`, `set_end_point`, `set_companies` + singular/plural variants), `set_base_segment(segment, copy=True)`, `add_segment(segment, conditions=...)`, `add_condition(cond)`, `add_drop_off(drop, conditions=...)`, `copy()`.
  - `build()` takes NO arguments — resolves `Condition` AST → SQLAlchemy `BinaryExpression`, builds JOINs, WHERE (date range, type filter, start/end points, company filter, global conditions), ORDER BY, and eager loading (start_point, end_point, company, prices→container, services).
  - `.unique()` required on result when prices collection is `contains_eager` loaded.
  - No pre-compilation — all aliases created fresh per `build()` call.

**Feature flags in route calculation (DB-backed settings):**

| Setting group | Setting name | Type | Default | Effect |
|---------------|-------------|------|---------|--------|
| `feature-flag` | `hide-sea-soc` | `BOOL` | `false` | When `true`, sea segments with `container_owner == SOC` are excluded from SQL queries (both direct SEA and combined sea+rail) |
| `feature-flag` | `rail-direct` | `BOOL` | `true` | When `true`, enables RAIL direct route calculation |
| `feature-flag` | `sea-direct` | `BOOL` | `true` | When `true`, enables SEA direct route calculation |
| `feature-flag` | `sea-rail` | `BOOL` | `true` | When `true`, enables SEA→RAIL combined route calculation |
| `feature-flag` | `rail-sea` | `BOOL` | `false` | When `true`, enables RAIL→SEA combined route calculation (TODO: production-ready) |
| `feature-flag` | `head-truck` | `BOOL` | `true` | When `true`, allows prepending a TRUCK segment before the route (via `truck_start_point_id`) |
| `feature-flag` | `tail-truck` | `BOOL` | `true` | When `true`, allows appending a TRUCK segment after the route (via `truck_end_point_id`) |
| `feature-flag` | `demo-excluded-fields` | `JSON` | `["company"]` | List of fields to blur for demo users |

- All 7 route-related flags are read in `data/internal/aggregators/routes.py` → `find_all_paths()` via `get_setting_cached("feature-flag", name)` using the `_flags` list — they are the configuration of our own data, so the source reads them
- The rules of the result are applied by the service (`services/route_calculation.py`): `deduplicate_routes()` keeps the first of the routes with the same segments, `mark_expired_routes()` marks the routes that hold a segment which is not valid anymore (`may_be_invalid`)
- `demo-excluded-fields` is read once per request, when the caller context is bound
- All settings are defined in `data/repositories/settings_definitions.py` and auto-synced to DB on startup via `ensure_settings()`
- Falls back to default value if setting not found or Redis/DB unavailable

**TRUCK segment connection rules (in `data/repositories/routes.py`):**
- `_connect_segments(prev, curr)` adds: `prev.end_point == curr.start_point`
- `_connect_segments_reversed(curr, _next)` adds: `curr.end_point == _next.start_point` (uses `q.prepend_segment()`)
- Head truck: `_attach_head_trucks` prepends truck segment before the first segment via `_connect_segments_reversed`
- Tail truck: `_attach_tail_trucks` appends truck segment after the last segment via `_connect_segments`
- **"Without delivery" button**: `build_queries` copies the base queries before attaching the truck segments, so the routes without the delivery are kept. The frontend filters out the TRUCK segments to show the non-truck routes.
- `_connect_rail` requires either SOC container owner or matching company + COC for the rail connection

### CLI Tools (`Python/cli/`)

**Entry point:** `cd Python && uv run python -m cli <command>`.
For sheets commands, also set `GSHEETS_URL` and `GOOGLE_SERVICE_ACCOUNT_PATH` env vars
(or put them in `.env.cli` in the project root — see `.env.cli.example`).
**Framework:** `click` (transitive dep via uvicorn; no explicit dependency needed)
**Auth:** `cli login` reads credentials from `.env.cli` (`ADMIN_USER`, `ADMIN_PASSWORD`),
or accepts `--username`/`--password` (higher priority). No interactive prompt.
Token stored in `~/.opencode-token`; sent as `Cookie: access_token_cookie=<token>`.

**Commands:**

```
python -m cli login                         # Authenticate from .env.cli or --args
python -m cli logout                        # Clear saved JWT
python -m cli route-query                   # Query route calculator API
python -m cli db list <resource>            # List resources via Admin API
python -m cli db get <resource>/<id>        # Get single resource
python -m cli db create <resource>          # Create resource (--data JSON)
python -m cli db update <resource>/<id>     # Full update PUT (--data JSON)
python -m cli db patch <resource>/<id>      # Partial update PATCH (--data JSON)
python -m cli db delete <resource>/<id>     # Delete resource
python -m cli db stats route-segments       # Bulk segment stats (type, through, owner, top companies)
python -m cli sheets worksheets             # List worksheets
python -m cli sheets columns <ws>           # List column names + 0-based indices
python -m cli sheets show <ws>              # Show data (--filter, --search, --columns, --csv, --output, --count)
python -m cli sheets search <ws>            # Search (--column optional, --columns, --limit)
python -m cli sheets find <company>         # Cross-worksheet company search (--columns, --csv, --output, --count)
```

All output is JSON by default (for AI/script parsing).

### Admin CRUD API (`data_browser.py`)

**File:** `Python/apps/entrypoints/admin/api/data_browser.py`
**Prefix:** `/db` (auto-discovered by `autodiscover.py`)
**Auth:** JWT via `Depends(bind_caller_context)`

**Resources and endpoints:**

| Resource | Endpoints | Description |
|----------|-----------|-------------|
| Companies | `GET/POST /db/companies`, `GET/PUT/PATCH/DELETE /db/companies/{id}` | `name: str` |
| Points | `GET/POST /db/points`, `GET/PUT/PATCH/DELETE /db/points/{id}` | `city, country, RU_city?, RU_country?` |
| Containers | `GET/POST /db/containers`, `GET/PUT/PATCH/DELETE /db/containers/{id}` | `size, type(DC/HC), weight_from, weight_to, name` |
| Route Segments | `GET/POST /db/route-segments`, `GET /db/route-segments/stats`, `GET/PUT/PATCH/DELETE /db/route-segments/{id}` | Composite: route fields + nested `prices[]` + `services[]` |
| Services | `GET/POST /db/services`, `GET/PUT/PATCH/DELETE /db/services/{id}` | `name, internal_name, description, hint?, mandatory, default` |
| Drop-off | `GET/POST /db/drop-off`, `GET/PUT/PATCH/DELETE /db/drop-off/{id}` | `container_id, company_id, dates, price, currency` |
| Settings | `GET/POST /db/settings`, `GET/PUT/PATCH/DELETE /db/settings/{id}` | `group, name, description?, value_type, value?` |

**Architecture:**
- `entrypoints/admin/api/data_browser.py` — thin route definitions only (delegates to the repositories)
- `data/repositories/admin/schemas.py` — all Pydantic request/response models with `from_model()` classmethods
- `data/repositories/admin/crud_base.py` — generic `CRUDBase` template (ABC) with `list`, `get`, `create`, `update`, `patch`, `delete` + filter definitions via `FilterDef`
- `data/repositories/admin/crud_*.py` — per-entity classes that override `_build_instance`, `_apply_update`, `_apply_patch` for entity-specific conversion logic (strip, enum/date parsing, nested prices/services)

**Route Segment** is a composite resource — `crud_route_segments.py` overrides `create`/`update` to handle nested `prices[]` and `services[]` (fully replaced on PUT); PATCH only touches route-level fields via `_apply_patch`. The `get` method uses `selectinload` for eager relationship loading.
- `RouteSegmentListResponse` includes `is_through` and `container_owner`
- `RouteSegmentStatsResponse` is returned by `GET /db/route-segments/stats`: totals, type/through/owner distribution, top 20 companies

**Settings CRUD** (`crud_settings.py`) — value validation:
- `parse_setting_value(value, value_type)` in `shared/dto/setting.py` is a standalone function (also used by `SettingItem._parse_value` validator)
- `_validate_value()` static method wraps it, raising `ValidationError` on parse failure
- `_build_instance` / `_apply_update` validate against `data.value_type` (known from request)
- For PATCH: `patch()` method is overridden — gets the model from DB first, validates `data.value` against `data.value_type or model.value_type`, then calls `_apply_patch` (which does no value validation)
- **Locked settings** (`model.locked`): PUT, DELETE, PATCH on group/name/type are blocked with `ValidationError`; only `value` is editable for locked settings

**The CRUD owns its session:** every public method of `CRUDBase` opens `get_database().session_context()` itself, so the admin API hands over the data and gets the answer — no session in the signatures and no SQL in the entrypoints. The data layer raises the domain errors of `shared/dto/errors.py` (`NotFoundError`, `ValidationError`, `ResourcePermissionError`); `shared/domain_error_handler.py` translates them into HTTP responses (404, 422, 403) and both apps register it.

---

## Makefile (`Makefile`)

| Target | Description |
|--------|-------------|
| `make build` | Docker buildx bake (all targets) |
| `make prod` | `docker compose up` — Ctrl+C runs `down` |
| `make dev` | `./scripts/run-dev.sh` — Ctrl+C runs `./scripts/stop-dev.sh` |
| `make test` | `./scripts/run-test.sh` — pytest in Docker (profile `test`) |
| `make lint` | Backend + frontend lint |
| `make lint-backend` | pre-commit (isort, flake8, mypy, pyupgrade) via uv |
| `make lint-frontend` | ESLint + build (user-frontend), ESLint (admin-frontend) |
| `make alembic [args]` | `./scripts/alembic-proxy.sh` — pass alembic subcommand via args |

---

### Cache Pitfalls

- `find_all_paths` in `data/fesco/api_client/routes.py` must call `list(data)` on the fetch result because `transform_routes` returns a `map` object (consumable iterator). Without `list()`, the background write of the cache would exhaust the iterator before serialization.
- The cache is policy driven: without a row in `cache_policies` the entity is not cached at all, so a test that expects a cache hit must give the source a policy.

### FESCO API Client Tests

All tests in `test_fesco_api_client.py` that call `get_containers`, `get_departure_points_by_date`, `get_destination_points_by_date`, or `find_all_paths` mock the HTTP session:
- `data.fesco.api_client.containers.aiohttp.ClientSession`
- `data.fesco.api_client.points.aiohttp.ClientSession`
- `data.fesco.api_client.routes.aiohttp.ClientSession`

The cache tests use a `LocalStorage` instead of a mocked Redis, and the backend of the source is built with a policy.

### The Static Checks (without the containers)

The project can not run `uv sync` in every environment, so the following checks are done with the standard library only and are worth repeating after every change:
- the import graph of the packages — every `from X import Y` must resolve
- the targets of `mock.patch(...)` — the module and the attribute must exist
- `python3 -m compileall` — the syntax of every file
- `isort --check-only` — the order of the imports

---

## ✅ Critical Rule

**After EVERY completed step** (every commit, every config change, every dependency update, every new file) — **STOP and update this AGENTS.md file** with any relevant new conventions, decisions, or structural changes. This file is the persistent memory for all future sessions. If it's not in AGENTS.md, it doesn't exist.
