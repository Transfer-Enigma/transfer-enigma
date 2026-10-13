# Query Domain — Declarative Route Query Builder

Builds SQLAlchemy `Select` statements for multi-segment route queries using a fluent API and an AST-based condition system.

## Files

| File | Exports | Purpose |
|------|---------|---------|
| `__init__.py` | `RouteBuilder`, `Segment`, `DropOff` | Package re-exports |
| `expr.py` | `ColumnRef`, `PriceRef`, `Condition`, `Connector` | AST nodes for column references and conditions |
| `segment.py` | `Segment` | Route segment domain entity with column access via `__getattr__` |
| `drop_off.py` | `DropOff` | Drop-off entity with column access and `exists()` |
| `builder.py` | `RouteBuilder` | Fluent API + SQL compilation |

---

## Core Concepts

### AST (`expr.py`)

**ColumnRef** — a reference to a table column. Created implicitly when accessing a named attribute on `Segment` or `DropOff` (via `__getattr__`). Also accessible through `PriceRef`.

Methods return `Condition` AST nodes:

| Method | SQL Equivalent |
|--------|----------------|
| `.equals(other)` | `column = other` |
| `.not_(other)` | `NOT column` |
| `.not_equals(other)` | `column != other` |
| `.not_null()` | `column IS NOT NULL` |
| `.null()` | `column IS NULL` |
| `.in_(values)` | `column IN (values)` |
| `.lte(value)` | `column <= value` |
| `.gte(value)` | `column >= value` |

**PriceRef** — references a price table column for a given segment. Created internally; the only exposed property is `.container` → `ColumnRef("container_id")`.

**Condition** — AST node with:

| Field | Type | Used by |
|-------|------|---------|
| `op` | `str` | All: `"eq"`, `"not"`, `"is_not_null"`, `"is_null"`, `"in"`, `"lte"`, `"gte"`, `"and"`, `"or"` |
| `left` | `ColumnRef \| None` | Binary ops (`eq`, `in`, `lte`, `gte`) |
| `right` | `Any` | Binary ops (literal value or another `ColumnRef`) |
| `operand` | `ColumnRef \| Condition \| None` | Unary ops (`not`, `is_not_null`, `is_null`) |
| `operands` | `list[Condition] \| None` | N-ary ops (`and`, `or`) |

**Connector** — static helpers for composing conditions:

```python
Connector.and_(a.equals(b), c.not_null())  # AND
Connector.or_(x.null(), y.exists())        # OR
```

### Segment (`segment.py`)

Wraps a `RouteModel` table row. The `_COLUMN_MAP` maps domain names to database column names:

| Domain Name | DB Column | Hidden `_id` |
|-------------|-----------|--------------|
| `type` | `type` | — |
| `is_through` | `is_through` | — |
| `container_owner` | `container_owner` | — |
| `effective_from` | `effective_from` | — |
| `effective_to` | `effective_to` | — |
| `start_point` | `start_point_id` | yes |
| `end_point` | `end_point_id` | yes |
| `company` | `company_id` | yes |
| `drop_off_point` | `dropp_off_point_id` | yes |

Access via attribute: `segment.start_point` → `ColumnRef(self, "start_point_id")`.

Constructor: `Segment(_type=RouteType.SEA)` or `Segment(_type="SEA")`. Accepts `RouteType` enum or string. The `_type_filter` is used in SQL WHERE.

### DropOff (`drop_off.py`)

Wraps a `DropModel` table row. `_COLUMN_MAP`:

| Domain Name | DB Column |
|-------------|-----------|
| `id` | `id` |
| `company` | `company_id` |
| `container` | `container_id` |
| `start_point` | `start_point_id` |
| `end_point` | `end_point_id` |
| `effective_from` | `effective_from` |
| `effective_to` | `effective_to` |

`.exists()` → `self.id.not_null()` — a condition that asserts the drop-off row exists (used in WHERE clauses for routes that require a drop-off).

---

## RouteBuilder API

### Instantiation

```python
builder = RouteBuilder(date)  # datetime.date for date-range filtering
```

### Setters (chainable, return `Self`)

| Method | Type | Description |
|--------|------|-------------|
| `set_containers(ids)` | `list[int]` | Filter prices by container IDs |
| `set_container(id)` | `int` | Single container |
| `set_start_point(id)` | `int` | First segment's `start_point_id` |
| `set_start_points(ids)` | `list[int]` | Multiple start points (OR) |
| `set_end_point(id)` | `int` | Last segment's `end_point_id` |
| `set_end_points(ids)` | `list[int]` | Multiple end points (OR) |
| `set_companies(ids)` | `list[int]` | Filter all segments by company |
| `set_company(id)` | `int` | Single company |

### Segment Management

```python
builder.add_segment(segment, conditions=[...])
# or
builder.add_segment(segment, conditions=prev.end_point.equals(curr.start_point))
```

- `add_segment` — append a segment with optional edge conditions (JOIN clause between this segment and the previous one)
- `prepend_segment` — insert at the beginning with edge conditions
- If no segments exist yet, `conditions` become global WHERE conditions

### Global Conditions & Drops

```python
builder.add_condition(condition)                    # Global WHERE clause
builder.add_drop_off(drop, conditions=[...])        # LEFT JOIN DropModel
```

### clone

```python
builder.copy()  # Shallow clone; segments, conditions, drops are copied by value
```

### Compilation

```python
query: Select = builder.build()
```

`build()` creates a `sqlalchemy.Select` with:

1. **Aliases** — each segment, price, service, and drop gets a unique aliased table (`seg_0`, `price_0`, `svc_0`, `drop_0`, etc.)
2. **Segment JOINs** — INNER JOIN for each additional segment with resolved edge conditions
3. **Price JOINs** — Each segment is INNER JOINed to its prices table, filtered by `container_id IN (...)`
4. **Drop LEFT JOINs** — optional drop-off tables
5. **WHERE** — type filter, date range (`effective_from <= date AND effective_to >= date`), start/end point filters, company filter, global conditions
6. **ORDER BY** — `effective_to DESC` for all segments
7. **Eager loading** — `start_point`, `end_point`, `company`, `prices → container`, `services → service`

---

## Usage Example

From `aggregators/routes.py`:

```python
def _connect_sea_rail(q, prev, curr, container_ids, date, *, hide_sea_soc=False):
    drop = DropOff()
    q.add_segment(curr, conditions=[
        prev.end_point.equals(curr.start_point),
        RouteBuilder.Connector.or_(
            RouteBuilder.Connector.and_(curr.is_through.not_(), prev.is_through.not_()),
            prev.company.equals(curr.company),
        ),
        RouteBuilder.Connector.or_(
            curr.container_owner.equals(ContainerOwner.SOC),
            RouteBuilder.Connector.and_(
                prev.company.equals(curr.company),
                curr.container_owner.equals(ContainerOwner.COC),
            ),
        ),
    ])
    q.add_condition(RouteBuilder.Connector.or_(
        prev.drop_off_point.not_null(),
        drop.exists(),
    ))
    q.add_drop_off(drop, conditions=[
        prev.drop_off_point.null(),
        curr.start_point.equals(drop.start_point),
        curr.end_point.equals(drop.end_point),
        drop.container.in_(container_ids),
        prev.company.equals(drop.company),
        drop.effective_from.lte(date),
        drop.effective_to.gte(date),
    ])
    if hide_sea_soc:
        q.add_condition(prev.container_owner.not_equals(ContainerOwner.SOC))


def build_simple_query(date, start, end, container_ids):
    base = RouteBuilder(date)
    base.set_containers(container_ids)
    base.set_start_point(start)
    base.set_end_point(end)

    sea = Segment(_type=RouteType.SEA)
    rail = Segment(_type=RouteType.RAIL)

    q = base.copy().add_segment(sea)
    _connect_sea_rail(q, sea, rail, container_ids, date)
    return q.build()
```

---

## Tests

Query domain unit tests in `tests/test_query_domain_*.py`:

| File | Test count | Scope |
|------|------------|-------|
| `test_query_domain_expr.py` | 19 | `ColumnRef`, `Condition`, `Connector` construction |
| `test_query_domain_segment.py` | 11 | `Segment` column access, `__repr__` |
| `test_query_domain_drop_off.py` | 6 | `DropOff` column access, `exists()`, `__repr__` |
| `test_query_domain_builder.py` | 19 | `RouteBuilder` API + DB-backed `build()` tests |
