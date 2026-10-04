# E2E in headless Chromium (workflow #1)

Headless Playwright tests against the full stack on **synthetic data only**
(`seed.sql`: 3 points, 2 companies, 2 containers, 3 RAIL segments, no real
secrets). Every test takes explicit screenshots into `e2e/screenshots/`
(`screenshot: 'on'` in the config additionally captures failures).

## Layout

- `package.json` — only devDep is `@playwright/test`.
- `playwright.config.ts` — headless Chromium, `baseURL` from `E2E_BASE_URL`
  (default `http://localhost:80`), `screenshot: 'on'`,
  `trace: 'on-first-retry'`.
- `tests/smoke.spec.ts` — home calculator opens, broken demo UID shows 404,
  admin login page opens.
- `tests/calculator.spec.ts` — departure/destination selection via API + UI,
  route calculation, routes list renders.
- `seed.sql` — minimal synthetic dataset, idempotent (`ON DUPLICATE KEY`).
- Selectors: `data-testid` first, graceful fallback to visible text
  (`getByTestId(...).or(getByRole/getByText(...))`).

## Run locally

```bash
# 1. Full stack (builds python-apps + reverseproxy with frontends locally;
# --load puts images into the local daemon so compose does not pull them)
TAG=e2e-local docker buildx bake --load -f docker-bake.hcl python-apps db-migration reverseproxy

# 2. Minimal .env (values below are CI-safe fallbacks, not secrets)
cat > .env <<'EOF'
DOCKER_PROD_IMAGES_TAG="e2e-local"
ENVIRONMENT="test"
DB_USER="e2e_user"
DB_PASS="e2e_pass"
DB_NAME="e2e_db"
DB_HOST="database"
DB_PORT=3306
ADMIN_LOGIN="e2e_admin"
ADMIN_PASSWORD="e2e_admin_pass"
AUTHJWT_SECRET_KEY="e2e-test-secret-key-not-for-prod"
APP_PORT=80
APP_SSL_PORT=443
REDIS_HOST="redis"
REDIS_PORT=6379
REDIS_DB=0
FESCO_API_KEY=
DEFAULT_GSHEETS_URL="https://docs.google.com/spreadsheets/d/e2e-synthetic"
DEFAULT_SEA_ROUTES_WS="SEA"
DEFAULT_RAIL_ROUTES_WS="RAIL"
DEFAULT_TRUCK_ROUTES_WS="TRUCK"
DEFAULT_DROPP_ROUTES_WS="DROPP"
DEFAULT_POINTS_WS="POINTS"
DEFAULT_SERVICES_WS="SERVICES"
EOF

# 3. Self-signed cert (prod nginx template listens on 443).
# 644: reverseproxy drops ALL capabilities, so the key must be world-readable.
mkdir -p cert
openssl req -x509 -nodes -days 2 -newkey rsa:2048 \
  -keyout cert/server.key -out cert/server.crt -subj "/CN=localhost"
cp cert/server.crt cert/ca.crt
chmod 644 cert/server.key cert/server.crt cert/ca.crt

# 4. DB + migrations + full stack
docker compose up -d database redis
docker compose -f docker-compose.migrate.yml run --rm dbmigrator upgrade head
docker compose up -d calculator auth backadmin reverseproxy

# 5. Wait for healthy, then seed
until curl -fsS http://localhost:80/ && curl -fsS http://localhost:80/api/openapi.json; do sleep 5; done
docker compose exec -T database mariadb -ue2e_user -pe2e_pass e2e_db < e2e/seed.sql

# 6. Playwright (headless Chromium)
cd e2e
npm ci
npx playwright install --with-deps chromium
npx playwright test

# Screenshots: e2e/screenshots/**, HTML report: e2e/playwright-report/
```

Teardown: `docker compose down -v` from the repo root.
