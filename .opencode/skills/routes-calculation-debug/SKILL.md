---
name: routes-calculation-debug
description: >
  Use when debugging route calculation issues (missing routes, wrong prices, etc.)
  in the Transfer Enigma project. Provides CLI tools for querying routes,
  browsing the database, and reading Google Sheets source data.
---

# AI Debug Tools — Transfer Enigma

This skill covers the debugging toolkit for route calculation in the Transfer Enigma
project. Use these tools when investigating why certain routes don't appear for
specific queries, or when verifying data consistency between Google Sheets, the
database, and API responses.

## CLI Tools

All tools run from the `Python/` directory with `PYTHONPATH=Python/apps`:

```bash
cd Python
export PYTHONPATH=Python/apps
python -m cli <command>
```

Or use inline env vars:
```bash
PYTHONPATH=Python/apps python -m cli <command>
```

### Configuration

CLI settings (URLs, secrets) are loaded from `Python/.env.cli`

Copy the example and fill in the values:

```bash
cp .env.cli.example .env.cli
# Edit .env.cli with your values:
#   GSHEETS_URL — Google Sheets URL
#   GOOGLE_SERVICE_ACCOUNT_PATH — path to service account JSON
#   ADMIN_USER / ADMIN_PASSWORD — admin credentials
#   API_BASE_URL, ADMIN_API_BASE_URL, AUTH_API_URL — API endpoints
```

`.env.cli` is in `.gitignore` — it won't be committed.

### Authentication

```bash
python -m cli login
# Token saved to ~/.opencode-token
python -m cli logout
```

Requires `ADMIN_LOGIN` and `ADMIN_PASSWORD` env vars (see above).

### Tool 1: Route Query — Test route calculation

```bash
python -m cli route-query \
  --date 2024-06-01 \
  --departure "1,2" \
  --destination "3,4" \
  --weight 12 \
  --type 20
```

_Weight limit - 28_

Accepts `--departure-ext` and `--destination-ext` for external (FESCO) point IDs.
Use `--demo-uid <uid>` to test as a demo user (profit overrides applied).
Output is JSON with `routes` and `errors`.

### Tool 2: Database Browser — Admin CRUD via API

```bash
python -m cli db list companies
python -m cli db list route-segments --filter company_id 1
python -m cli db get route-segments/42
python -m cli db create companies --data '{"name": "New Co"}'
python -m cli db update companies/1 --data '{"name": "Updated"}'
python -m cli db patch companies/1 --data '{"name": "Partial"}'
python -m cli db delete companies/1
```

Valid resources: `companies`, `points`, `containers`, `route-segments`,
`services`, `drop-off`.

### Tool 3: Google Sheets Reader

Requires `GSHEETS_URL` and `GOOGLE_SERVICE_ACCOUNT_PATH` env vars (see above).

```bash
python -m cli sheets worksheets                          # List all worksheets

# Column discovery (always start here)
python -m cli sheets columns МОРЕ                        # List column names + 0-based indices

# Show data with filtering
python -m cli sheets show МОРЕ --limit 20                # First 20 rows (default)
python -m cli sheets show МОРЕ --limit 0                 # ALL rows (be careful with large sheets)
python -m cli sheets show МОРЕ --offset 100 --limit 20   # Paginate
python -m cli sheets show МОРЕ --count                   # Just count rows
python -m cli sheets show МОРЕ --search "NECOLINE"       # Search across ALL columns
python -m cli sheets show МОРЕ --filter "Линия=NECOLINE" # Filter by column=value
python -m cli sheets show МОРЕ --columns "0,5,6"         # Select columns by index
python -m cli sheets show МОРЕ --columns "Линия"         # Select columns by name

# Output options
python -m cli sheets show МОРЕ --csv                     # CSV output to stdout
python -m cli sheets show МОРЕ --csv --output /tmp/sea.csv  # Save to file
python -m cli sheets show МОРЕ \
  --filter "Линия=NECOLINE" \
  --columns "0,2,5,6" \
  --csv --output /tmp/necoline.csv                       # Combined: filter + select + export

# Search within a worksheet
python -m cli sheets search МОРЕ --value "NECOLINE"          # All-column search (like grep)
python -m cli sheets search МОРЕ --column 5 --value "NECOLINE"  # Search specific column by index
python -m cli sheets search МОРЕ --column "Линия" --value "NECOLINE"  # ...or by name
python -m cli sheets search МОРЕ --value "DPN" --count         # Count matches
python -m cli sheets search МОРЕ --value "NECOLINE" --limit 5 --columns "0,2,5,6" --csv

# Cross-worksheet company search (KILLER FEATURE for debugging)
python -m cli sheets find DPN                             # Find DPN in ALL worksheets
python -m cli sheets find NECOLINE --columns "5,6"        # Selected columns + worksheet name
python -m cli sheets find DPN --count                     # Count per worksheet
python -m cli sheets find DPN --csv --output /tmp/dpn_all_sheets.csv  # Export all
```

**Pro tip**: Always start with `sheets columns <ws>` to see column names and their 0-based indices.
For column names containing commas (e.g., `Сквозной маршрут (1 - да, 0 - нет)`), use their numeric index (`6`).
Use `sheets find <company>` when you need to check what data exists for a carrier across both sea and rail sheets simultaneously.

## Admin CRUD API

All endpoints under `/admin/api/db/` on port 8082, JWT-protected.

| Resource | Endpoints |
|----------|-----------|
| Companies | `GET/POST /db/companies`, `GET/PUT/PATCH/DELETE /db/companies/{id}` |
| Points | `GET/POST /db/points`, `GET/PUT/PATCH/DELETE /db/points/{id}` |
| Containers | `GET/POST /db/containers`, `GET/PUT/PATCH/DELETE /db/containers/{id}` |
| Route Segments | `GET/POST /db/route-segments`, `GET/PUT/PATCH/DELETE /db/route-segments/{id}` |
| Services | `GET/POST /db/services`, `GET/PUT/PATCH/DELETE /db/services/{id}` |
| Drop-off | `GET/POST /db/drop-off`, `GET/PUT/PATCH/DELETE /db/drop-off/{id}` |

### Route Segment composite format

Route Segment is a composite resource — POST/PUT accept nested `prices[]` and
`services[]`. PATCH updates only route-level fields (not prices/services).
Prices and services are fully replaced on PUT.

### Typical debugging workflow

1. **Check source data in Google Sheets** — use `sheets find <company>` to see all
   data across sea (МОРЕ) and rail (ЖД) sheets. Use `--count` for a quick overview,
   then `--columns "col1,col2" --csv --output /tmp/file.csv` for detailed analysis.

2. **Verify import correctness** — use `db list route-segments --filter company_id N`
   to check data was imported correctly (especially `is_through`, `container_owner`,
   `type`, point IDs).

3. **Test route calculation** — use `route-query` with specific parameters. If routes
   are missing, compare the DB data against the Google Sheets source using the
   workflow above.

4. **Inspect full records** — use `db get route-segments/{id}` to see prices,
   services, and all fields of a specific segment.

5. **Cross-reference terminals** — use `sheets find <terminal_name>` to see which
   companies serve which terminals. Use `db list` to check exact point IDs in the
   database vs the Google Sheets source.
