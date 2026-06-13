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
│   ├── backend_auth/         # Port 8081 — Auth & demo guest login
│   │   └── main.py           # FastAPI app: /login, /token/refresh, /logout, /me
│   ├── backend_user/         # Port 8080 — Route calculator (user-facing API)
│   │   ├── main.py
│   │   ├── autodiscover.py
│   │   ├── config.py
│   │   ├── api/v1/, api/v2/  # Versioned API endpoints
│   │   ├── dependencies/
│   │   └── services/
│   ├── backend_admin/        # Port 8082 — Admin data management
│   │   ├── main.py
│   │   ├── autodiscover.py
│   │   ├── api/
│   │   │   ├── routes_loading.py  # Import routes from Google Sheets
│   │   │   ├── data_manager.py    # DB dump/erase/load
│   │   │   ├── demo_guests.py     # CRUD demo guests
│   │   │   └── data_browser.py    # Thin CRUD routes (delegates to service/)
│   │   ├── schemas/
│   │   │   └── data_browser.py    # Pydantic request/response models
│   │   └── service/
│   │       ├── crud_base.py           # Generic CRUD template (CRUDBase)
│   │       ├── crud_companies.py      # Company CRUD service
│   │       ├── crud_points.py         # Point CRUD service
│   │       ├── crud_containers.py     # Container CRUD service
│   │       ├── crud_route_segments.py # Route segment CRUD (composite)
│   │       ├── crud_services.py       # Service CRUD service
│   │       └── crud_drop_off.py      # Drop-off CRUD service
│   ├── module_shared/
│   ├── module_data_internal/
│   └── module_data_fesco_api_adapter/
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
│       ├── pages/        # Login, Dashboard, DataImport, DemoGuests
│       ├── api/          # Axios API clients (Auth, Data, DemoGuests)
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

**Package Manager:** Poetry (`pyproject.toml` at project root). Always use `poetry add` CLI, don't edit `pyproject.toml` manually.

**Dependency groups:**
| Group | File | Contents |
|-------|------|----------|
| `[tool.poetry.dependencies]` | `Python/requirements.txt` | Runtime deps |
| `[tool.poetry.group.dev.dependencies]` | `Python/requirements-dev.txt` | Linting/pre-commit tools (black, pre-commit, ipython) |
| `[tool.poetry.group.tests.dependencies]` | `Python/requirements-tests.txt` | Test frameworks (pytest, pytest-asyncio, httpx, aiosqlite) |

**Export commands** (run after every `poetry add` / `poetry remove`):
```bash
poetry export -f requirements.txt --output Python/requirements.txt --without-hashes
poetry export -f requirements.txt --output Python/requirements-dev.txt --without-hashes --with dev
poetry export -f requirements.txt --output Python/requirements-tests.txt --without-hashes --with tests
```

The `.txt` files are what the Docker build uses, so they must stay in sync with `poetry.lock`.

**Dockerfile stages** (`Python/Dockerfile`):
| Stage | Base | Purpose |
|-------|------|---------|
| `python-apps` | `python:3.12-slim` | Runs FastAPI microservices via uvicorn |
| `db-migration` | `python:3.12-slim` | Runs Alembic database migrations |
| `test-runner` | `python:3.12-slim` | Runs pytest (install from `requirements-tests.txt`) |

The `test-runner` stage copies `apps/` to `/app/apps/`, `tests/` to `/app/tests/`, and overrides rootdir via `--override-ini` flags (no pyproject.toml in build context). At runtime, the hot-dev compose mounts `pyproject.toml` for config.

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
- `Auth Backend:` — `backend_auth` only
- `User Backend:` — `backend_user` only
- `Admin Backend:` — `backend_admin` only
- `Python:` — crosses multiple Python modules (e.g., adding shared code)
- `User Frontend:` — Vue app only
- `Admin Frontend:` — React app only
- `Database:` — Alembic migrations, SQL scripts
- `Nginx:` — Nginx config changes
- `Docs:` — Documentation only
- `CI:` — CI/CD workflow changes

### Pre-Commit Checks
- Before each Python commit: `pre-commit run --all-files` — this catches lint/type errors early, avoiding fix commits on top
- Before each Node commit: run the project's lint script (if available)
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
- Max line length: 120 chars
- Max McCabe complexity: 10
- Existing flake8 plugins: `flake8-builtins`, `flake8-comprehensions`, `flake8-eradicate`, `flake8-expression-complexity`, `flake8-simplify`, `flake8-bugbear`, `flake8-pie`, `flake8-print`, `flake8-noqa`, `flake8-broken-line`
- Router auto-discovery pattern: place `router = APIRouter(...)` in any module under `api/` — it gets discovered automatically
- DB sessions: use `async with db.session_context() as session` — auto-commits on exit, auto-rollbacks on exception
- Alembic migrations: placed in `Python/alembic/versions/`, excluded from pre-commit (`exclude: 'Python/alembic/.*'`)

### Python Tests
- Tests live in `Python/tests/`, run with `pytest`
- **71 tests** across 7 files:
    - `test_route_calculation.py` (18) — route calculation (service-level: internal, FESCO, mixed, errors; handler-level: format conversion, demo transforms/strip/profit)
    - `test_internal_aggregators.py` (17) — containers, paths (rail/sea/COC/SOC/expired/services/drop/dropp_off/no_data/process_results)
    - `test_profit.py` (17) — currency conversion, profit application, segment type filtering, mixed segments, currency conversion in profit
    - `test_auth_utils.py` (8) — `_strip_demo_fields`, `get_auth_context` with/without/invalid demo header, empty routes
    - `test_get_points.py` (4) — `get_departure_points`, `get_destination_points`, no routes, multiple companies
    - `test_demo_guest_repo.py` (5) — `get_demo_guest_by_uid` found/not found/profit overrides, `list_demo_guests` empty/multiple
    - `test_get_rates.py` (3) — `get_rates` returns dict, caching, with datetime
- **Test DB**: SQLite in-memory (`sqlite+aiosqlite`). Tables created via `Base.metadata.create_all()`, **not** via Alembic migrations (migrations have MySQL-specific code).
- **Auth mocks**: patch `get_demo_guest_by_uid`, `get_database`, and `request_auth` directly
- **FESCO API mocks**: use `unittest.mock.patch` on `module_data_fesco_api_adapter.api_client` directly
- **Test data**: factory functions in `Python/tests/data/__init__.py` build ORM objects with sensible defaults
- **Currency rates**: tests use RUB-relative rates `{"USD": 90.0, "RUB": 1.0}`; `_convert_currency` formula is `amount * rates[from] / rates[to]`
- Run locally: `PYTHONPATH=Python/apps python -m pytest Python/tests/ -v`
- Run in Docker (profile `test`, won't start with `docker compose up`):
  `./scripts/run-test.sh`

### Python Module Dependencies Graph
```
module_shared ───┬── backend_auth
                 ├── backend_user ───┬── module_data_internal
                 │                   └── module_data_fesco_api_adapter
                 └── backend_admin ─── module_data_internal
```

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
- Python: `pre-commit run --all-files`
- Frontends: check `package.json` for lint scripts

---

## Architecture & Design Decisions

### API Versioning
- User API uses URL versioning: `/v1/`, `/v2/`
- Auth and Admin APIs are not versioned

### Auth Flow
1. Login sets JWT access + refresh cookies (httpOnly)
2. Frontend refreshes token on interval via `POST /token/refresh`
3. Demo users authenticate via `X-Demo-User-UID` header (no JWT, no backend_auth)

### Demo Guest Feature
- Admin creates demo guests with UID + profit overrides (stored in `demo_guests` table)
- Demo link format: `/demo/<UID>`
- All demo auth is in `backend_user` — `backend_auth` is NOT involved
- Backend: `get_auth_context` dependency checks `X-Demo-User-UID` header → looks up `demo_guests` table → returns `AuthContext` (is_demo, profit overrides). If no header, falls through to JWT via `request_auth`.
- V2 endpoints use `Depends(get_auth_context)` (supports both JWT and header auth)
- V1 endpoints use `Depends(request_auth)` (JWT only)
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

**`module_shared/models/route.py`** — Route entities (Pydantic V2 `BaseModel`):
- Models: `ContainerItem`, `PriceItem`, `OnePrice`, `ServiceItem`, `DropItem`, `RouteSegment`, `RouteResult`
- `OnePrice` represents FESCO single-price format with `beginCond`/`finishCond` (price-level conditions, set only for sea segments)
- `PriceItem` represents internal multi-price format (always has `value: float`)
- `RouteSegment.prices` can be `list[PriceItem]` (internal) or `OnePrice` (FESCO) or `None`

**`module_shared/models/errors.py`** — Error model:
- `RouteError(error_type: str, error_text: str, source: str | None)`
- Used in services (no source) and points handlers (`"internal"`/`"external"`)

### Service/API Separation (Single Responsibility)
- **Services** (`backend_user/services/`) handle data work: fetching, aggregating, manipulating (e.g., `_strip_demo_fields`)
- **API handlers** (`backend_user/api/`) handle format conversion: model → tuple for HTTP response
- Models in `module_shared/models/route.py` are Pydantic V2 `BaseModel` (not dataclasses) — they serve as both domain objects and response schemas
- `calculate_routes()` returns `tuple[list[RouteResult], list[RouteError]]` (raw Pydantic models + errors)
- V2 handler (`api/v2/routes/post.py`) owns: `_route_result_to_tuple`, `_normalize_routes`, `_apply_demo_transforms`
  - `_seg_to_price_dict` was removed — models are returned as-is (no OnePrice flattening to `price`/`currency`/`container`/`beginCond`/`finishCond` flat fields)
  - Response format: `[segments: list[RouteSegment], drop: DropItem | None, bool, services: list[ServiceItem]]` — tuple with raw model objects
- V1 handler (`api/v1/routes/post.py`) has its own copies of these functions (legacy, separate format)
- `_strip_demo_fields` stays in `services/route_calculation.py` (data manipulation, not format conversion)
- No duplicate Pydantic response models — `backend_user/schemas/routes_responses.py` imports `RouteSegment`, `DropItem`, `ServiceItem` from `module_shared.models.route`

### Database
- MariaDB, accessed via SQLAlchemy async + `aiomysql`
- Migrations via Alembic
- Models defined in `module_data_internal/schemas/` and `module_shared/schemas/`
- Both use the same `Base` class from `module_shared.database`

### CLI Tools (`Python/cli/`)

**Entry point:** `python -m cli <command>` (requires `PYTHONPATH=Python/apps`).
For sheets commands, also set `GSHEETS_URL` and `GOOGLE_SERVICE_ACCOUNT_PATH` env vars
(or put them in `Python/.env`).
**Framework:** `click` (transitive dep via uvicorn; no explicit dependency needed)
**Auth:** JWT login via `POST /login` on backend_auth; token stored in `~/.opencode-token`; sent as `Cookie: access_token_cookie=<token>` in subsequent requests. `api/user/` nginx route is used by default.

**Commands:**

```
python -m cli login                         # Authenticate and save JWT
python -m cli logout                        # Clear saved JWT
python -m cli route-query                   # Query route calculator API
python -m cli db list <resource>            # List resources via Admin API
python -m cli db get <resource>/<id>        # Get single resource
python -m cli db create <resource>          # Create resource (--data JSON)
python -m cli db update <resource>/<id>     # Full update PUT (--data JSON)
python -m cli db patch <resource>/<id>      # Partial update PATCH (--data JSON)
python -m cli db delete <resource>/<id>     # Delete resource
python -m cli sheets worksheets             # List worksheets
python -m cli sheets columns <ws>           # List column names + 0-based indices
python -m cli sheets show <ws>              # Show data (--filter, --search, --columns, --csv, --output, --count)
python -m cli sheets search <ws>            # Search (--column optional, --columns, --limit)
python -m cli sheets find <company>         # Cross-worksheet company search (--columns, --csv, --output, --count)
```

All output is JSON by default (for AI/script parsing).

### Admin CRUD API (`data_browser.py`)

**File:** `Python/apps/backend_admin/api/data_browser.py`
**Prefix:** `/db` (auto-discovered by `autodiscover.py`)
**Auth:** JWT via `Depends(request_auth)`

**Resources and endpoints:**

| Resource | Endpoints | Description |
|----------|-----------|-------------|
| Companies | `GET/POST /db/companies`, `GET/PUT/PATCH/DELETE /db/companies/{id}` | `name: str` |
| Points | `GET/POST /db/points`, `GET/PUT/PATCH/DELETE /db/points/{id}` | `city, country, RU_city?, RU_country?` |
| Containers | `GET/POST /db/containers`, `GET/PUT/PATCH/DELETE /db/containers/{id}` | `size, type(DC/HC), weight_from, weight_to, name` |
| Route Segments | `GET/POST /db/route-segments`, `GET/PUT/PATCH/DELETE /db/route-segments/{id}` | Composite: route fields + nested `prices[]` + `services[]` |
| Services | `GET/POST /db/services`, `GET/PUT/PATCH/DELETE /db/services/{id}` | `name, internal_name, description, hint?, mandatory, default` |
| Drop-off | `GET/POST /db/drop-off`, `GET/PUT/PATCH/DELETE /db/drop-off/{id}` | `container_id, company_id, dates, price, currency` |

**Architecture:**
- `api/data_browser.py` — thin route definitions only (delegates to service layer)
- `schemas/data_browser.py` — all Pydantic request/response models with `from_model()` classmethods
- `service/crud_base.py` — generic `CRUDBase` template (ABC) with `list`, `get`, `create`, `update`, `patch`, `delete` + filter definitions via `FilterDef`
- `service/crud_*.py` — per-entity service classes that override `_build_instance`, `_apply_update`, `_apply_patch` for entity-specific conversion logic (strip, enum/date parsing, nested prices/services)

**Route Segment** is a composite resource — `crud_route_segments.py` overrides `create`/`update` to handle nested `prices[]` and `services[]` (fully replaced on PUT); PATCH only touches route-level fields via `_apply_patch`. The `get` method uses `selectinload` for eager relationship loading.

---

## Makefile (`Makefile`)

| Target | Description |
|--------|-------------|
| `make build` | Docker buildx bake (all targets) |
| `make prod` | `docker compose up` — Ctrl+C runs `down` |
| `make dev` | `./scripts/run-dev.sh` — Ctrl+C runs `./scripts/stop-dev.sh` |
| `make update [args]` | `./scripts/prod-update.sh` — pass args directly |
| `make export-deps` | `./scripts/export-python-dependencies.sh` |
| `make alembic [args]` | `./scripts/alembic-proxy.sh` — pass alembic subcommand via args |
| `make migrate [args]` | `./scripts/prod-db-migrate.sh` — pass alembic subcommand via args |

## Route Calculation — Debugging Findings

### `containerType` is actually container size, not DC/HC type
- The API field `containerType` is passed as `size` to `search_container_ids()` (`containers.py:19-24`), which filters by `ContainerModel.size` column (20 or 40 feet).
- The DC/HC type (`ContainerModel.type`) is never used for filtering in the calculate endpoint.
- CLI `--type` help was fixed to read "Container size in feet (20 or 40)" — previously said "Container type (0=DC, 1=HC)".
- Frontend sends `containerType` as string `"20"` or `"40"` — correct.

### COC/SOC matching logic
File: `routes.py:_apply_container_owner_filter` (lines 270-296):
- Same company → Rail must be `container_owner == COC`
- Different companies → Rail must be `container_owner == SOC`
- Both sea and rail must be from the same `RouteDate` (same effective range)

### Through-route condition
File: `routes.py` — the sea-rail JOIN includes:
```python
or_(
    ~RailRoute.is_through & ~SeaRoute.is_through,  # both non-through
    SeaRoute.company_id == RailRoute.company_id,    # same company
)
```
A `is_through: true` rail segment cannot pair with a non-through sea segment from a different company.

### NECOLINE (965/1109) findings
- **May** (2026-05-15 to 2026-05-31): Has COC sea segments from Ningbo/Shanghai → Vostochniy/ППК-1 (7299) → COC+COC combo works.
- **June** (2026-06-01 to 2026-06-30): Only SOC sea segments from Ningbo/Shanghai → Vostochniy/ППК-1 (7299) + COC rail → SOC+COC combo works (same-company rule requires COC rail ✓). COC sea simply doesn't exist for June.
- **No COC-only route possible** because there's no COC-only path (you'd need a direct route, or both sea and rail COC + same company = same result).

### DPN (984/1103) findings
- **30 segments, all RAIL, zero SEA.** Start points: 7299 (ППК-1), 7300 (ВРАНГЕЛЬ), 6787 (Nahodka) — all to Moscow (7037).
- `is_through: true` in DB (sheet says `0` = not through), `container_owner: SOC` on all checked segments.
- Cannot form sea+rail routes because:
  1. No SEA segments at all.
  2. Through rail cannot pair with other companies' non-through sea (through condition blocks it).
  3. Even if it could pair, NECOLINE's non-through sea would be blocked by through condition.

### RTG (1010/1066) findings
- Has SEA segments (from Taiwan, other Asian ports — NOT from Ningbo/Shanghai) to Vostochniy/ВРАНГЕЛЬ (7300).
- Has RAIL segments from 7300 → Moscow, `container_owner: SOC`, `is_through: true` in DB (sheet says `0` = not through).
- Through rail + different company non-through sea → blocked by through-route condition.
- Even without the through condition, no sea from Chinese ports exists for RTG.

### Root cause: `is_through` importer bug in uploader.py:249
- The importer inverts the `is_through` flag for ALL segments.
- Sheet column "Сквозной маршрут (1 - да, 0 - нет)": `1` = through, `0` = not through.
- Buggy code: `is_throw = pd.isna(...) or is_throw_raw == 0.0 or is_throw_raw == "0"` — treats `"0"` (not through) as `True` (through).
- Fix: invert the condition to `not (pd.isna(...) or is_throw_raw == 0.0 or is_throw_raw == "0")`.

### Impact of the bug
- **DPN / RTG** (rail `is_through=0` in sheets → DB `true`): blocked from pairing with other companies' non-through sea. DPN has 30 rail segments (SOC, from Врангель/ППК-1), zero sea. RTG has its own sea but same-company COC/SOC rule blocks internal pairing (rail SOC + sea requires rail COC).
- **NECOLINE** (rail/sea `is_through=1` in sheets → DB `false`): MORE permissive than intended — current route display works because same-company combos bypass through-route check.
- **All carriers** have inverted `is_through` — the bug is universal.

### After the fix, these routes should appear:
- DPN SOC rail + any non-through sea from another company to Врангель/ППК-1 (e.g., MOHILL, RUSCON, HUA XIN)
- RTG SOC rail + any non-through sea from another company to Врангель
- NECOLINE sea+rail (same company) still works as before

### Terminal mapping
- ППК‑1 = DB point 7299 (exclusive NECOLINE terminal, 650 sea segments)
- Врангель = DB point 7300 (shared terminal, 1457 sea segments from 24 companies)
- Early (April) data may have used different point IDs (6803/6804) — after re-import, all use the new IDs.

---

## ✅ Critical Rule

**After EVERY completed step** (every commit, every config change, every dependency update, every new file) — **STOP and update this AGENTS.md file** with any relevant new conventions, decisions, or structural changes. This file is the persistent memory for all future sessions. If it's not in AGENTS.md, it doesn't exist.
