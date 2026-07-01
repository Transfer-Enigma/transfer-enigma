# Skill: add-route-type

Add a new route segment type (e.g., `AUTO`, `AIR`) to the Transfer Enigma route
calculator — from DB schema through frontend icons.

> **Before starting**, read the template files under `reference/` in this skill
> to understand the patterns used.

---

## Surface Area

These files MUST be touched for every new segment type:

```
Python/
├── apps/
│   ├── module_data_internal/
│   │   ├── schemas/route.py           # 1. RouteType enum
│   │   └── aggregators/routes.py      # 2. templates + find_all_paths
│   ├── backend_admin/
│   │   ├── config.py                  # 3. worksheet name config
│   │   ├── api/routes_loading.py      # 4. download + display mapping
│   │   ├── models/uploader_fields_config.py  # 5. price columns
│   │   ├── service/routes_loading/
│   │   │   ├── uploader.py            # 6. create_route branches
│   │   │   └── processor.py           # 7. process_routes_df branches
│   │   └── schemas/data_browser.py    # 8. type comment
│   └── backend_user/services/profit.py  # 9. profit branch
├── alembic/versions/                  # 10. migration
└── tests/                             # 11. integration tests

Node/
└── apps/
    ├── user-frontend/src/
    │   ├── interfaces/Routes.ts       # 12. TS enum
    │   ├── components/RouteTypeIcon.vue # 13. SVG icon
    │   └── services/calculator.ts     # 14. legacy check
    └── old-user-frontend/js/calculating.js  # 15. icons map
```

Files that do NOT need changes (`type` is `str` or generic):
- `module_shared/models/route.py` — `RouteSegment.type: str`
- `module_shared/schemas/route.py` — ORM `type` column uses `Enum(RouteType)`
- `query_domain/segment.py` — generic `RouteType` field
- `query_domain/compiler.py` — generic `alias.type == seg_def.route_type`
- `aggregators/transformers/routes.py` — generic `route.type.name`
- `service/crud_route_segments.py` — generic `RouteType(type_filter.upper())`

---

## Step-by-Step Workflow

### Step 1 — RouteType enum
In `module_data_internal/schemas/route.py`, add to `class RouteType(enum.Enum)`:
```python
AUTO = "AUTO"
```

### Step 2 — Route templates
In `module_data_internal/aggregators/routes.py`:

**2a.** Direct template:
```python
def _newtype_direct() -> Route:
    return Route(segments=[_base_segment(RouteType.NEWTYPE)], connections=[])
```

**2b.** Combined templates with rail/sea:
```python
def _rail_newtype_combined() -> Route:
    rail = (
        RouteSegment(RouteType.RAIL)
        .add_filter(EffectiveOn())
        .add_filter(AtStartPoint())
    )
    newtype = (
        RouteSegment(RouteType.NEWTYPE)
        .add_filter(EffectiveOn())
        .add_filter(AtEndPoint())
    )
    return Route(
        segments=[rail, newtype],
        connections=[
            RouteSegmentConnection(from_seg=rail, to_seg=newtype)
            .rule(MatchesEndpoint()),
        ],
    )
```

Use `MatchesEndpoint` for simple connections. Use `DropAwareEndpoint` +
`CocSocLogic` + `ThroughLogic` + `_sea_rail_drop()` when the combined route
includes a SEA↔RAIL connection.

**2c.** Pre-compiled compilers:
```python
_rail_newtype_compiler = QueryCompiler(_rail_newtype_combined())
```
Add one per template.

**2d.** In `find_all_paths()`, add to `all_queries`:
```python
_rail_newtype_compiler.build(date, start_point_id, end_point_id, container_ids),
```

### Step 3 — Alembic migration
Create a new migration in `Python/alembic/versions/`:
```python
"""Add NEWTYPE to RouteType enum"""

from alembic import op

revision = "xxxxxxx"
down_revision = "previous_revision"


def upgrade() -> None:
    op.execute('ALTER TABLE `routes` MODIFY COLUMN `type` ENUM("SEA", "RAIL", "NEWTYPE")')


def downgrade() -> None:
    op.execute('ALTER TABLE `routes` MODIFY COLUMN `type` ENUM("SEA", "RAIL")')
```

The ENUM must list ALL existing types plus the new one, since MySQL replaces
the entire enum definition.

### Step 4 — Admin config
In `backend_admin/config.py`, add:
```python
DEFAULT_NEWTYPE_ROUTES_WS: str = Field(default="НОВЫЙ_ЛИСТ", alias="NEWTYPE_WS")
```

### Step 5 — Admin routes_loading.py
- Add `newtype_routes_ws_name: str = DEFAULT_NEWTYPE_ROUTES_WS` query param
- Add download block for the new worksheet
- Update `routes_ws` display mapping:
  ```python
  {RouteType.SEA: "МОРЕ", RouteType.RAIL: "ЖД", RouteType.NEWTYPE: "НОВЫЙ", None: "ДРОПП"}
  ```

### Step 6 — Uploader fields config
In `uploader_fields_config.py`, add price column names:
```python
"newtype_20dc": "_newtype_20dc",
"newtype_40hc": "_newtype_40hc",
```
Or whatever columns the new type's worksheet uses.

### Step 7 — Uploader create_route()
In `uploader.py`, add a branch:
```python
if route_type == RouteType.NEWTYPE:
    prices = _extract_newtype_prices(row, price_fields)
    ...
```
For currency columns too.

### Step 8 — Processor
In `processor.py`, add `RouteType.NEWTYPE` handling in:
- `process_routes_df()` — price field filtering
- `load_data()` — concatenation
- Terminal-point concatenation

### Step 9 — Profit service
In `backend_user/services/profit.py`, add:
```python
elif seg_type == "newtype":
    profit = newtype_profit
    profit_currency = newtype_profit_currency or profit_currency
```

### Step 10 — Data browser comment
In `schemas/data_browser.py`, update:
```python
type: str  # "SEA", "RAIL", or "NEWTYPE"
```

### Step 11 — Frontend TS enum
In `Node/apps/user-frontend/src/interfaces/Routes.ts`:
```typescript
export enum RouteType {
    SEA = "SEA",
    RAIL = "RAIL",
    NEWTYPE = "NEWTYPE",
    SEA_RAIL = "SEA_RAIL",  // legacy, keep
}
```

### Step 12 — RouteTypeIcon.vue
Ensure an SVG sprite with `id="NEWTYPE"` exists in the icons file, or it falls
into the `v-else` branch which uses `type.toUpperCase()` as the icon reference.

### Step 13 — Old frontend icons map
In `calculating.js`, add to `icons` map or the `||` fallback displays the raw
type string.

### Step 14 — Tests
In `test_query_domain.py`: helpers, template tests, compiler tests.

In `test_internal_aggregators.py`: integration tests for direct + combined
routes using `RouteFactory(type=RouteType.NEWTYPE)`.

Run:
```bash
pre-commit run --all-files
pytest Python/tests/
```

---

## Connection Rule Decision Tree

When choosing connection rules between two segments:

```
from_seg → to_seg
├── If to_seg is middle (connected on both sides):
│   └── MatchesEndpoint ── the simplest ── from.end == to.start
├── If this is a SEA→RAIL or RAIL→SEA full combo:
│   ├── SEA→RAIL (forward, with port drop-off):
│   │   └── DropAwareEndpoint + CocSocLogic + ThroughLogic + _sea_rail_drop()
│   └── RAIL→SEA (reverse, no drop-off):
│       └── MatchesEndpoint
└── If either segment is AUTO (or new type without drop-off):
    └── MatchesEndpoint
```

## Filter Decision Tree

```
Segment position
├── First segment: Add AtStartPoint()  → dep_id
├── Last segment:  Add AtEndPoint()    → dest_id
├── Middle segment: No point filter    → connected by rules
└── Any position:  Add EffectiveOn()  → date range filter

Segment type
├── SEA with hide_sea_soc=True: Add ExcludeOwners([ContainerOwner.SOC])
├── Direct segment:               Add NoDropOff() via _base_segment()
└── Combined segment first leg:   Omit NoDropOff() (may have drop-off point)
```

