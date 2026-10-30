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

Import root is `Python/apps` (`pythonpath = ["apps"]` in `pyproject.toml`), so modules are imported as
`shared.*`, `entrypoints.*`, `services.*`, `data.*` (top-level absolute imports, no `apps.` prefix).

```
Python/
├── cli/                   # CLI debugging tools (AI-assisted route debugging)
│   ├── main.py            # click group: login, route-query, db, sheets
│   ├── auth.py            # JWT login, token storage (~/.opencode-token)
│   ├── config.py          # CLISettings: API_BASE_URL, ADMIN_API_BASE_URL, etc.
│   ├── route_query.py     # Tool 1: Query /v2/routes/calculate via API
│   ├── db_explorer.py     # Tool 2: Admin CRUD client (list, get, create, update, patch, delete)
│   └── sheets_reader.py   # Tool 3: Google Sheets reader (worksheets, show, search)
├── apps/                  # import root
│   ├── entrypoints/       # FastAPI applications
│   │   ├── auth/          # Port 8081 — main.py: /login, /token/refresh, /logout, /me
│   │   ├── user/          # Port 8080 — route calculator (user-facing API)
│   │   │   ├── main.py, autodiscover.py
│   │   │   ├── api/           # v2/, v3/ (SSE) versioned endpoints
│   │   │   ├── dependencies/  # auth.py (JWT), auth_context.py (JWT + X-Demo-User-UID)
│   │   │   ├── schemas/       # form_requests, routes (RouteSegment/DropItem/ServiceItem), errors, get_points_responses
│   │   │   └── utils/         # group_points.py
│   │   └── admin/         # Port 8082 — admin data management
│   │       ├── main.py, autodiscover.py, responses*.py
│   │       ├── api/
│   │       │   ├── routes_loading.py  # Import routes from Google Sheets (API layer)
│   │       │   ├── data_manager.py    # DB dump/erase/load
│   │       │   ├── demo_guests.py     # CRUD demo guests
│   │       │   └── data_browser.py    # Thin CRUD routes (delegates to service/)
│   │       ├── dependencies/auth.py   # JWT via Depends(request_auth)
│   │       ├── models/upoader_fields_config.py  # Google Sheets column-name config
│   │       ├── schemas/data_browser.py          # Pydantic request/response models
│   │       └── service/
│   │           ├── crud_base.py           # Generic CRUD template (CRUDBase)
│   │           ├── crud_companies.py      # Company CRUD service
│   │           ├── crud_points.py         # Point CRUD service
│   │           ├── crud_containers.py     # Container CRUD service
│   │           ├── crud_route_segments.py # Route segment CRUD (composite)
│   │           ├── crud_services.py       # Service CRUD service
│   │           ├── crud_drop_off.py       # Drop-off CRUD service
│   │           ├── crud_settings.py       # Settings CRUD service
│   │           ├── db_management/         # db_dumper, db_eraser, db_loader
│   │           └── routes_loading/        # Sheets import pipeline
│   │               ├── processor.py       # df cleanup, defaults, point/service sheets
│   │               ├── uploader.py        # ORM model creation (create_route, create_route_service, create_dropp)
│   │               ├── helpers.py         # nan_to_none_mapper, price_filter, format_date
│   │               └── errors.py          # PointNotFound, CompanyNotFound, NoPriceInRoute, ...
│   │   └── initializer/   # One-shot seeding: settings + cache policies
│   ├── services/          # cross-entrypoint business logic
│   │   ├── routes/            # calculation.py — calculate_routes orchestration
│   │   ├── rates/             # get.py — CBR rates + cache fallback
│   │   ├── demo/              # profit.py — demo profit + currency conversion
│   │   ├── cache/             # backend.py (CacheBackend), registry.py (CacheRegistry), refresh.py (policy refresh), seed.py
│   │   └── settings/          # seed.py — ensure_settings (creates missing settings rows + writes cache)
│   ├── shared/            # shared kernel (old module_shared)
│   │   ├── config.py, database.py, logger.py, resources.py, jwt_error_handler.py
│   │   ├── redis_client.py       # Redis async singleton (get_redis / get_redis_client)
│   │   ├── settings.py, setting_definitions.py
│   │   ├── models/               # Domain models (models/): ContainerItem, PriceItem, OnePrice, ServiceItem, DropItem, RouteSegment, RouteResult, SettingItem, CacheEntity, CachePolicy
│   │   ├── orm/                  # SQLAlchemy models + enums (old schemas/): company, container, demo_guest, drop, point, route, service, setting, cache_policy
│   │   ├── repositories/         # demo_guest.py, setting.py (get/list helpers)
│   │   └── concurrency/          # Locker ABC, LocalLocker, RedisLocker, TaskAlreadyRunningError
│   └── data/              # data sources
│       ├── internal/      # internal DB data (old module_data_internal)
│       │   ├── aggregators/    # containers, points, routes (find_all_paths, feature flags)
│       │   └── query_domain/   # declarative query builder (README.md inside)
│       ├── fesco/         # FESCO API adapter (old module_data_fesco_api_adapter)
│       │   ├── cache.py        # per-entity backend getters (get_routes_backend(date) etc.), FESCO_SOURCE
│       │   └── api_client/     # containers, points, routes, transformers
│       ├── cache/         # cache primitives: cache_policies.py (defaults + ensure_cache_policies + MULTI_SOURCE_ENTITIES + is_multi_source), storage/ (protocol, local, redis)
│       └── setings/       # NOTE: package name is "setings" (one 't') — cached.py: get_setting_cached / set_settings_cache / delete_settings_cache
```

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

**Hot-dev bind mounts** (`docker-compose.hot-dev.yml`, `docker-compose.hot-dev.backend.yml`): sources are mounted per-directory over the image (mounting all of `apps/` would hide `/workspace/.venv`). When adding a new top-level package under `Python/apps/` (e.g. `data/cache`), add an `:ro` bind mount to the affected services in **both** hot-dev files — otherwise the container imports the stale image copy and fails with `ModuleNotFoundError` for new packages. Currently mounted: `entrypoints/{user,admin,auth,initializer}`, `data/`, `shared`, `services` (in `hot-dev.yml` `data/` and `services/` are mounted whole for calculator/backadmin; in `hot-dev.backend.yml` also whole, except `initializer` which mounts `data/cache`, `data/setings` and `services/` per-directory). Alembic files are **not** mounted — rebuild `db-migration` (`docker buildx bake db-migration`) and run `docker compose -f docker-compose.migrate.yml run --rm dbmigrator upgrade head` for new migrations.

### Redis Caching

**Status:** Active — Redis service available in all environments (prod, dev, test).

**Redis client:** `shared/redis_client.py` — async singleton via `get_redis()` / `get_redis_client()`. Connection pool managed by `redis.asyncio`.
- `decode_responses=True` — all values are strings (JSON serialized)
- Config: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` from `shared/config.py`

**Shared cache package** (`Python/apps/data/cache/` + `Python/apps/services/cache/`):
- `data/cache/storage/protocol.py` — `CacheStorage` Protocol (`get`/`set`/`delete`/`delete_prefix`/`keys`)
- `data/cache/storage/local.py` — `LocalStorage` — in-process storage; `set(key, value, ttl=None)` — `ttl=None` means no expiry, invalidated explicitly
- `data/cache/storage/redis.py` — `RedisStorage` — Redis-backed storage
- `services/cache/backend.py` — `CacheBackend(storage, entity, policies)` — per-entity cache access with `get`/`set`/`delete`/`set_async`/`silent_set_async`; keys built as ``[source:]entity:parts`` where source comes from the policy (None for single-source entities). Also exports `cache_prefix(entity, source)` and `flush_cache(storage, entity, source)` for explicit invalidation
- `entries(limit)` on the backend (backed by `CacheStorage.keys(prefix, limit)` in `storage/`) reads back up to `limit` key/value pairs of one policy — used by the admin `GET /{id}/entries` endpoint
- `shared/dto/cache.py` — `CacheEntity` StrEnum (departures, destinations, containers, routes, points, rates, settings + `*_TODAY` variants) + `CachePolicy` dataclass (`source: str | None, entity, enabled, ttl`; source is None for single-source entities)
- `data/cache/cache_policies.py` — default (source, entity, enabled, ttl) rows + `ensure_cache_policies()` (fills missing rows only) + `MULTI_SOURCE_ENTITIES` + `is_multi_source(entity)`
- `data/cache/__init__.py` — empty; import `CacheEntity`/`CachePolicy` from `shared.dto.cache`

**Cache registry** (`Python/apps/services/cache/registry.py`):
- `CacheRegistry` — loads policies from the `cache_policies` table and builds per-entity `CacheBackend` instances; there is no local policy cache
- `registry.load()` — reads policies from DB, validates source/entity combinations, rebuilds backends **only when the policy set changed** (returns `True` then, `False` otherwise, so an unchanged refresh keeps in-flight `silent_set_async` writes)
- `registry.backend(entity, source=None)` — returns or builds a `CacheBackend` for the entity
- `get_cache_registry()` — per-process cached singleton
- `services/cache/refresh.py` — `refresh_policies(interval)`, `start_policy_refresh()` and the `policy_refresh()` context manager; **both** user and admin reload policies every `CACHE_POLICIES_REFRESH_INTERVAL_SECONDS` (default `10`, `0` disables). Admin also reloads its registry immediately after cache policy writes, so the calculator is the only process that waits for the periodic refresh
- `services/cache/seed.py` — `do_seed()` wrapper around `ensure_cache_policies()` for the initializer

**Cache key scheme** (storage key = ``[source:]entity:parts``):

| Data | Source | Entity | Key pattern | TTL | Eviction |
|------|--------|--------|-------------|-----|----------|
| Currency rates | (none) | rates | `rates:latest` | from policy | volatile-lru |
| FESCO departures | fesco | departures | `fesco:departures:{date}` | from policy | volatile-lru |
| FESCO destinations | fesco | destinations | `fesco:destinations:{date}:{dep_id}` | from policy | volatile-lru |
| FESCO routes | fesco | routes | `fesco:routes:{date}:{dep}:{dest}:{wte_ids}` | from policy | volatile-lru |
| FESCO containers | fesco | containers | `fesco:containers:{date}:{dep_id}:{dest_id}` | from policy | volatile-lru |
| FESCO departures (today) | fesco | departures_today | `fesco:departures_today:{date}` | from policy | volatile-lru |
| FESCO destinations (today) | fesco | destinations_today | `fesco:destinations_today:{date}:{dep_id}` | from policy | volatile-lru |
| FESCO routes (today) | fesco | routes_today | `fesco:routes_today:{date}:{dep}:{dest}:{wte_ids}` | from policy | volatile-lru |
| FESCO containers (today) | fesco | containers_today | `fesco:containers_today:{date}:{dep_id}:{dest_id}` | from policy | volatile-lru |
| Settings | (none) | settings | `settings:{group}:{name}` | from policy | volatile-lru |

**Today-policy fallback** (`data/fesco/cache.py` `get_*_backend(date)`): when `date` is today but the `*_today` policy is missing or disabled, the base-entity backend is used instead (base keys, base TTL). To turn caching off entirely, disable the base policy.

**Settings cache — transparent:** `Python/apps/data/setings/cached.py` implements cache-aside for DB-backed settings (note the package name is `setings`, one 't'):
- `get_setting_cached(group, name, *, session=None)` — Redis → DB → fire-and-forget write
- `set_settings_cache(item)` — write single setting to Redis
- `delete_settings_cache(group, name)` — remove single setting from Redis
- `backend_user` lifespan calls `get_redis_client().init()`, `get_cache_registry().load()` and runs the policy refresh loop
- `backend_admin` lifespan calls `get_redis_client().init()`, `get_cache_registry().load()` and runs the same policy refresh loop
- Admin settings CRUD endpoints use `BackgroundTasks` to set/delete Redis values after the DB write, so settings changes are visible immediately

**Rates flow:**
1. Always try CBR API first (`ExchangeRates`)
2. On success: return `(rates, today)` + `asyncio.create_task()` writes to Redis via `CacheBackend(CacheEntity.RATES)` (source=None)
3. On failure: fallback to Redis — return `(rates, cached_date)` from cache
4. If both fail: `RuntimeError`

**API endpoints:**
- `GET /v2/rates` — returns `{rates: {...}, updated_at: "2026-06-16"}` (adds date)

**Redis docker-compose:**
- `docker-compose.yml`: `valkey/valkey:alpine`, AOF+RDB persistence, `volatile-lru` (512mb maxmemory)
- `docker-compose.hot-dev.backend.yml`: extends redis from base
- `docker-compose.test.yml`: redis with 128mb maxmemory, `test` profile

**Admin cache policies API** (`/admin/api/cache/policies`):
- `GET` — list policies (filter by source, entity)
- `GET /{id}` — get single policy
- `POST` — create policy (validates source/entity combination); flushes the cache of that entity/source so stale data does not survive
- `PATCH /{id}` — update `enabled` and `ttl` only (`source`/`entity` are rejected, `ttl >= 1`); changing `enabled` does not delete cached data
- `DELETE /{id}` — delete policy; flushes the cache of that entity/source
- `POST /{id}/invalidate` — remove every cached value of one policy, returns `{deleted: N}`
- `POST /invalidate` — remove every cached value of every configured policy, returns `{deleted: N}`
- `GET /{id}/entries?limit=50` — read-only listing of what one policy holds right now; returns `{policy_id, prefix, count, entries: [{key, value}]}` with `limit` in `1..500` (values exactly as stored)

Every policy write calls `registry.load()` in the admin process (so its settings-cache writes honour the new policy immediately). Other processes pick changes up via their periodic refresh; a disabled policy stops reads/writes in the calculator at the next refresh, while its keys expire by TTL.

**Unified cache seeder** (`entrypoints/initializer/main.py`):
- Default settings live in `shared/setting_definitions.py`, default cache policies are defined inline in `data/cache/cache_policies.py` (all FESCO entities enabled TTL 3600s/86400s/600s; all `internal` entities disabled; `rates` enabled, `settings` disabled — seeding only fills missing rows)
- `ensure_settings()` (`services/settings/seed.py`) / `ensure_cache_policies()` (`data/cache/cache_policies.py`, wrapped by `services/cache/seed.py`) create only missing rows (existing rows are never touched); they are run by the one-shot initializer entrypoint (`entrypoints/initializer/main.py`), not by the user+admin lifespans
- One-shot service `initializer` (`docker-compose.yml` + `docker-compose.migrate.yml`): `python -m entrypoints.initializer.main`, exit 0 on success. `calculator` and `backadmin` start only after it completes (`depends_on: service_completed_successfully`); `prod-update.sh` runs migrate first, then `up -d` triggers the initializer

### Locker System

`shared/concurrency/` — lock/unlock abstraction for preventing duplicate concurrent operations:

- **`Locker` (ABC)** — sync/async `acquire`/`release`, context managers, class-level `@locked`/`@alocked` decorators that wrap functions with acquire/release semantics
- **`LocalLocker`** — in-process threading-based lock (`threading.Lock` + `dict[str, bool]`). Used by `CacheBackend.set_async` to prevent duplicate fire-and-forget writes for the same cache key
- **`RedisLocker`** — distributed Redis-based lock using `SET NX EX` (async only; sync methods raise `RuntimeError`)
- **`TaskAlreadyRunningError`** — raised on re-acquire

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
- `Auth Backend:` — `entrypoints/auth` (old `backend_auth`) only
- `User Backend:` — `entrypoints/user` (old `backend_user`) only
- `Admin Backend:` — `entrypoints/admin` (old `backend_admin`) only
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

### Currency Handling (always UPPERCASE)
Currency codes are stored and compared in **UPPPERCASE** (`USD`, `EUR`, `CNY`, `RUB`, `RUR`, `РУБ`); any lowercase
value coming from a Google Sheet cell or a `?currency=` URL param must be normalized with `.strip().upper()` before
lookup — a lowercase code must never raise "валюта не найдена" / `Invalid currency` / `Undefined rate`.

- **Google Sheets loader** (`entrypoints/admin/service/routes_loading/uploader.py`):
    - route price currencies: `row[...].strip().upper()` in `create_route` (empty → `"USD"` for SEA, `"РУБ"` for RAIL/TRUCK)
    - service price currencies: `str(currency or "").strip().upper() or "USD"` in `create_route_service`
    - drop-off currency is hardcoded `"USD"` (never read from the sheet)
- **User frontend normalizes at every lookup point** (data itself is left as-is):
    - `stores/rates.ts` — `setRates` uppercases rate keys; `setCurrentRate` uppercases the incoming value before the map lookup
    - `services/rates.ts` — `convertToCurrentRate` and `isConversationNeeded` uppercase their argument
    - `helpers/currency.ts` — `getCurrencySymbol` uppercases the symbol key
- **Rate aliases**: `RUB` = `RUR` = `РУБ` = 1 — injected by `services/rates/get.py`, listed in frontend `isConversationNeeded`
- **Not normalized yet**: admin CRUD payloads (`entrypoints/admin/schemas/data_browser.py`) and demo-guest profit
  currencies — they accept any string, so normalize (`field_validator`) if you touch those write paths.

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
    - `test_route_calculation.py` — route calculation (service-level: internal, FESCO, mixed, errors; handler-level: format conversion, demo transforms/strip/profit)
    - `test_internal_aggregators.py` — containers, paths (rail/sea/COC/SOC/expired/services/drop/dropp_off/no_data/process_results), hide-sea-soc + route-type feature flags + TRUCK routes (direct, truck→rail, rail→truck, truck→rail→truck, truck→sea→rail→truck, truck→rail→sea→truck, sea+rail with truck, base queries for "without delivery" button)
    - `test_profit.py` — currency conversion, profit application, segment type filtering, mixed segments, currency conversion in profit
    - `test_auth_utils.py` — `_strip_demo_fields`, `get_auth_context` with/without/invalid demo header, empty routes
    - `test_get_points.py` — `get_departure_points`, `get_destination_points`, no routes, multiple companies
    - `test_demo_guest_repo.py` — `get_demo_guest_by_uid` found/not found/profit overrides, `list_demo_guests` empty/multiple
    - `test_get_rates.py` — `get_rates` returns dict, caching, with datetime, API failure fallback
    - `test_setting_cache.py` — `get_setting_cached` cache hit/miss/not_found
    - `test_cache_registry.py` — CacheRegistry load/rebuild, policy refresh, today-backend fallback
    - `test_cache_seed.py` — `ensure_cache_policies` creates missing rows only
    - `test_fesco_api_client.py` — FESCO API transformations, container search, points, routes, caching
    - `test_deduplication.py` — route deduplication preserves distinct routes, multiple prices
    - `test_route_calculation_v3_sse.py` — SSE streaming, demo transforms, error handling
    - `test_query_domain_expr.py` — ColumnRef, Condition, Connector
    - `test_query_domain_builder.py` — RouteBuilder API tests + DB-backed build tests
    - `test_resources_base_path.py` — settings/base-path resolution
- **Test DB**: SQLite in-memory (`sqlite+aiosqlite`). Tables created via `Base.metadata.create_all()`, **not** via Alembic migrations (migrations have MySQL-specific code).
- **Auth mocks**: patch `get_demo_guest_by_uid`, `get_database`, and `request_auth` directly
- **FESCO API mocks**: use `unittest.mock.patch` on `data.fesco.api_client` directly
- **Test data**: factory functions in `Python/tests/factories.py` build ORM objects with sensible defaults
- **Currency rates**: tests use RUB-relative rates `{"USD": 90.0, "RUB": 1.0}`; `_convert_currency` formula is `amount * rates[from] / rates[to]`
- Run: `make test` (Docker, profile `test` — won't start with plain `docker compose up`)

### Python Module Dependencies Graph
```
shared ───┬── entrypoints/auth
          ├── entrypoints/user ─┬── data/internal
          │                     └── data/fesco
          ├── entrypoints/admin ── data/internal
          └── services/ (used by entrypoints/user)
```

### TypeScript / Frontends
- **User Frontend**: Vue 3 Composition API (`<script setup lang="ts">`), Pinia stores, Vue Router
- **Admin Frontend**: React 19 functional components, React Router, Axios for API
- Both use TypeScript, Bootstrap 5
- **`defineModel` typing (Vue ≥ 3.5.44)**: `default` was removed from `PropOptions` in the model options type
  (`DefineModelRuntimeOptions = Omit<PropOptions, 'default'> & DefineModelOptions`), so `default: undefined`
  no longer compiles for object-typed models (e.g. `defineModel<IdIsExternal[]>({ required: false, default: undefined })`
  → TS2769 + cascade TS2322 in the template). For optional models use `defineModel<T | undefined>({ required: false })`
  — no `default`. Scalar models (`string`/`boolean`) may still pass `default: ""` / `default: false`.
  Runtime is unaffected: `useModel()` ignores `options.default`.

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
- User API uses URL versioning: `/v2/`, `/v3/`
- Auth and Admin APIs are not versioned
- `/v3/routes/calculate` (POST) is an SSE endpoint for progressive route streaming — each route/error is yielded as an SSE event when available

### Auth Flow
1. Login sets JWT access + refresh cookies (httpOnly)
2. Frontend refreshes token on interval via `POST /token/refresh`
3. Demo users authenticate via `X-Demo-User-UID` header (no JWT, no backend_auth)

### Demo Guest Feature
- Admin creates demo guests with UID + profit overrides (stored in `demo_guests` table)
- Demo link format: `/demo/<UID>`
- All demo auth is in `entrypoints/user` (old `backend_user`) — `entrypoints/auth` is NOT involved
- Backend: `get_auth_context` dependency checks `X-Demo-User-UID` header → looks up `demo_guests` table → returns `AuthContext` (is_demo, profit overrides). If no header, falls through to JWT via `request_auth`.
- V2 endpoints use `Depends(get_auth_context)` (supports both JWT and header auth)
- Demo endpoints: `POST /api/v2/demo/validate` (validates UID), `GET /api/v2/demo/feature-flags` (returns blurred_fields list)
- Frontend: `helpers/requests.ts` → `demoHeaders()` reads `useDemoAuth()` Pinia store → injects `X-Demo-User-UID` into every `fetchAsJSON()` call
- Demo users see blurred company names via CSS class (driven by `useBlurredFields` composable ← `featureFlags` store)
- Profits (`sea_profit`, `rail_profit`) are added to route prices for demo users only (in profit service)
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

**`entrypoints/user/schemas/errors.py`** — Error model:
- `RouteError(error_type: str, error_text: str, source: str | None)`
- Used in services (no source) and points handlers (`"internal"`/`"external"`)

### Service/API Separation (Single Responsibility)
- **Services** (`services/`) handle data work: fetching, aggregating, manipulating (e.g., `_strip_demo_fields`)
- **API handlers** (`entrypoints/user/api/`) handle format conversion: model → tuple for HTTP response
- Models in `shared/dto/route.py` are Pydantic V2 `BaseModel` (not dataclasses) — they serve as both domain objects and response schemas
- `calculate_routes()` returns `tuple[list[RouteResult], list[RouteError]]` (raw Pydantic models + errors)
- V2 handler (`api/v2/routes/post.py`) owns: `_route_result_to_tuple`, `_normalize_routes`, `_apply_demo_transforms`
    - `_seg_to_price_dict` was removed — models are returned as-is (no OnePrice flattening to `price`/`currency`/`container`/`beginCond`/`finishCond` flat fields)
    - Response format: `[segments: list[RouteSegment], drop: DropItem | None, bool, services: list[ServiceItem]]` — tuple with raw model objects
- `_strip_demo_fields` stays in `services/routes/calculation.py` (data manipulation, not format conversion)
- No duplicate Pydantic response models — `entrypoints/user/schemas/routes.py` imports `RouteSegment`, `DropItem`, `ServiceItem` from `shared.models.route`

### Database
- MariaDB, accessed via SQLAlchemy async + `aiomysql`
- Migrations via Alembic
- All ORM models and enums defined in `shared/orm/`
- Both use the same `Base` class from `shared.database`

### Route Calculation — Key Logic

> Подробное описание логики расчёта маршрутов см. в [ROUTES-CALCULATION-LOGIC.md](./ROUTES-CALCULATION-LOGIC.md).

** Query Composer (`query_domain/`) —** wired into `routes.py` (replaced raw SQL `build_usual_query`/`build_base_sea_rail_query`). Full API docs in [`query_domain/README.md`](./Python/apps/data/internal/query_domain/README.md).
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

- All 7 route-related flags are read in `data/internal/aggregators/routes.py` → `find_all_paths()` via `get_setting_cached("feature-flag", name)` using the `_flags` list
- `demo-excluded-fields` is read in `entrypoints/user/api/v2/demo/feature_flags.py` and several point/route handlers
- All settings are defined in `shared/setting_definitions.py` and auto-synced to DB on startup via `initializer`
- Falls back to default value if setting not found or Redis/DB unavailable

**TRUCK segment connection rules (in `routes.py`):**
- `_connect_segments(prev, curr)` adds: `prev.end_point == curr.start_point`
- `_connect_segments_reversed(curr, _next)` adds: `curr.end_point == _next.start_point` (uses `q.prepend_segment()`)
- Head truck: `_attach_head_trucks` prepends truck segment before the first segment via `_connect_segments_reversed`
- Tail truck: `_attach_tail_trucks` appends truck segment after the last segment via `_connect_segments`
- **"Without delivery" button**: `build_queries` copies base queries before attaching truck segments, then returns `[base_queries + queries]`. The frontend filters out TRUCK segments to show non-truck routes.
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
**Auth:** JWT via `Depends(request_auth)`

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
| Cache Policies | `GET/POST /admin/api/cache/policies`, `GET/PATCH/DELETE /admin/api/cache/policies/{id}`, `POST /admin/api/cache/policies/{id}/invalidate`, `POST /admin/api/cache/policies/invalidate` | `source, entity, enabled, ttl` — CRUD; PATCH only `enabled`/`ttl`; create/delete flush the cache and every write reloads the admin registry; invalidation returns `{deleted: N}` |

**Architecture:**
- `api/data_browser.py` — thin route definitions only (delegates to service layer)
- `schemas/data_browser.py` — all Pydantic request/response models with `from_model()` classmethods
- `service/crud_base.py` — generic `CRUDBase` template (ABC) with `list`, `get`, `create`, `update`, `patch`, `delete` + filter definitions via `FilterDef`
- `service/crud_*.py` — per-entity service classes that override `_build_instance`, `_apply_update`, `_apply_patch` for entity-specific conversion logic (strip, enum/date parsing, nested prices/services)

**Route Segment** is a composite resource — `crud_route_segments.py` overrides `create`/`update` to handle nested `prices[]` and `services[]` (fully replaced on PUT); PATCH only touches route-level fields via `_apply_patch`. The `get` method uses `selectinload` for eager relationship loading.
- `RouteSegmentListResponse` includes `is_through` and `container_owner`
- `RouteSegmentStatsResponse` is returned by `GET /db/route-segments/stats`: totals, type/through/owner distribution, top 20 companies

**Settings CRUD** (`crud_settings.py`) — value validation and cache sync:
- `parse_setting_value(value, value_type)` in `shared/models/setting.py` is a standalone function (also used by `SettingItem._parse_value` validator)
- `_validate_value()` static method wraps it, raising `HTTPException(422)` on parse failure
- `_build_instance` / `_apply_update` validate against `data.value_type` (known from request)
- For PATCH: `patch()` method is overridden — gets the model from DB first, validates `data.value` against the **model's existing** `value_type`, then calls `_apply_patch` (which does no value validation)
- **Locked settings** (`model.locked`): PUT, DELETE, PATCH on group/name/type are blocked with `HTTP_403_FORBIDDEN`; only `value` is editable for locked settings
- Settings endpoints update/delete the Redis value via `BackgroundTasks` (`set_settings_cache`/`delete_settings_cache`), including deleting the old key after a group/name rename

**Cache management page** (admin frontend): `Node/apps/admin-frontend/src/pages/CachePolicies.tsx` — lists cache policies (source, entity, enabled, ttl), allows creating/deleting policies, editing only `enabled`/`ttl`, and invalidating one policy or all policies. Source field is shown only for multi-source entities and is a select of `CACHE_SOURCES` (`fesco`, `internal`) from `src/interfaces/CachePolicy.ts`. Wired at route `ROUTES.CACHE` (`/cache`) with a sidebar nav link. API client: `src/api/CachePolicies.ts`, interfaces: `src/interfaces/CachePolicy.ts`.

---

## Makefile (`Makefile`)

| Target | Description |
|--------|-------------|
| `make build` | Docker buildx bake (all targets) |
| `make prod` | `docker compose up` — Ctrl+C runs `down` |
| `make dev` | `docker compose -f docker-compose.hot-dev.yml up` — Ctrl+C runs `stop-dev.sh` |
| `make test` | `docker compose -f docker-compose.test.yml run --rm test-runner` — pytest in Docker (profile `test`) |
| `make lint` | Backend + frontend lint |
| `make lint-backend` | pre-commit (black, isort, flake8, mypy) via uv |
| `make lint-frontend` | ESLint + build (user-frontend), ESLint (admin-frontend) |
| `make alembic [args]` | `uv run --frozen alembic <args>` |

---

### Cache Pitfalls

- `find_all_paths` in `api_client/routes.py` must call `list(data)` on the fetch result because `transform_routes` returns a `map` object (consumable iterator). Without `list()`, `backend.silent_set_async(data=..., dump=True)` would exhaust the iterator before serialization. The `list()` call also ensures the result can be returned to the caller.
- Points caching (`api_client/points.py`) is safe because its fetch functions return plain JSON dicts/lists, not iterators.
- Container caching (`api_client/containers.py`) is also safe — `transform_containers` returns a sorted list.

### FESCO API Client Tests

All tests in `test_fesco_api_client.py` that call `get_containers`, `get_departure_points_by_date`, `get_destination_points_by_date`, or `find_all_paths` must mock `redis` because these functions now use Redis caching directly. The mock targets:
- `data.fesco.api_client.points.aiohttp.ClientSession` — for points (backends go through `cache.py`)
- `data.fesco.api_client.containers.get_containers_backend` — for containers
- `data.fesco.api_client.routes.get_routes_backend` + `data.fesco.api_client.routes.aiohttp.ClientSession` — for `find_all_paths`

---

## ✅ Critical Rule

**After EVERY completed step** (every commit, every config change, every dependency update, every new file) — **STOP and update this AGENTS.md file** with any relevant new conventions, decisions, or structural changes. This file is the persistent memory for all future sessions. If it's not in AGENTS.md, it doesn't exist.
