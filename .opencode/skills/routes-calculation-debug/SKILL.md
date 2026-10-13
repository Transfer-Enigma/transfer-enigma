---
name: routes-calculation-debug
description: >
  Use when debugging route calculation issues (missing routes, wrong prices, etc.)
  in the Transfer Enigma project. Provides CLI tools for querying routes,
  browsing the database, and reading Google Sheets source data.
---

# AI Debug Tools — Transfer Enigma

CLI tools for investigating route calculation issues: missing routes, wrong prices,
data consistency between Google Sheets → DB → API.

## CLI Reference

```bash
cd Python && uv run --group cli python -m cli <command>
```

Config from `.env.cli` (see `.env.cli.example`): URLs, GSHEETS_URL,
GOOGLE_SERVICE_ACCOUNT_PATH, admin credentials.

| Command | Description |
|---------|-------------|
| `login` | Auth via `.env.cli` credentials (or `--username`/`--password`) |
| `route-query` | Test route calculation (use `--help` for examples) |
| `db list <res>` | List resources with `--filter key value` |
| `db get <res>/<id>` | Get single record (prices/services for route-segments) |
| `db create <res>` | Create record (`--data JSON`) |
| `db update <res>/<id>` | Full update (`--data JSON`) |
| `db patch <res>/<id>` | Partial update (`--data JSON`) |
| `db delete <res>/<id>` | Delete record |
| `db stats route-segments` | Total/type/through/owner distribution, top companies |
| `sheets columns <ws>` | List column names + 0-based indices (start here) |
| `sheets show <ws>` | Show rows (`--search`, `--filter`, `--columns`, `--csv`, `--count`) |
| `sheets search <ws>` | Search across all columns or specific `--column` |
| `sheets find <company>` | Cross-worksheet company search |
| `sheets worksheets` | List all worksheet names |

Resources: `companies`, `points`, `containers`, `route-segments`, `services`, `drop-off`.

## Typical debugging workflow

1. **Check source data in Sheets** — `sheets find <company>` for all data across sea
   and rail sheets. `--count` for overview, `--csv --output /tmp/f.csv` for analysis.

2. **Verify import** — `db list route-segments --filter type SEA --filter company_id N`
   with `db stats route-segments` for bulk checks (is_through/owner distribution).

3. **Test calculation** — `route-query` with specific params. If routes missing,
   compare DB data against sheets via the workflow above.

4. **Inspect full records** — `db get route-segments/{id}` to see prices, services,
   `is_through`, `container_owner`.

5. **Cross-reference terminals** — `sheets find <terminal>` to see which companies
   serve which terminals; verify point IDs match between sheets and DB.
