import datetime
from dataclasses import dataclass

from module_data_internal.query_domain.connection import RouteSegmentConnection
from module_data_internal.query_domain.drop import DropConnection
from module_data_internal.query_domain.route import Route
from module_data_internal.schemas import DropModel, PriceModel, RouteModel, ServicePriceModel
from sqlalchemy import Select, and_, desc, select
from sqlalchemy.orm import aliased, contains_eager, joinedload, selectinload


@dataclass(frozen=True)
class DropSpec:
    """Pre-resolved drop-off: one DropConnection + its alias."""

    conn: RouteSegmentConnection
    drop: DropConnection
    alias: object


class QueryCompiler:
    """Compiles a Route domain model to a SQLAlchemy Select statement.

    Created once per Route; pre-computes all aliases in the constructor.
    ``build()`` compiles a fresh SELECT for the given query parameters.
    """

    def __init__(self, route: Route) -> None:
        self._route = route
        n = len(route.segments)

        self._seg_aliases: list[object] = [aliased(RouteModel, name=f"seg_{i}") for i in range(n)]
        self._price_aliases: list[object] = [aliased(PriceModel, name=f"price_{i}") for i in range(n)]
        self._svc_aliases: list[object] = [aliased(ServicePriceModel, name=f"svc_{i}") for i in range(n)]

        self._alias_map: dict[int, object] = {id(seg): al for seg, al in zip(route.segments, self._seg_aliases)}
        self._price_map: dict[int, object] = {id(seg): al for seg, al in zip(route.segments, self._price_aliases)}

        self._drop_specs: list[DropSpec] = self._resolve_drops(route)

    # ── public API ────────────────────────────────────────────────────

    def build(
        self,
        date: datetime.date,
        dep_id: int,
        dest_id: int,
        container_ids: list[int],
    ) -> Select:
        drop_aliases = [spec.alias for spec in self._drop_specs]

        stmt = self._build_select(drop_aliases)
        stmt = self._join_segments(stmt, container_ids)
        stmt = self._join_drops(stmt, date)
        stmt = self._apply_filters(stmt, dep_id, dest_id, date)
        stmt = self._apply_ordering(stmt)
        return self._apply_eager_loading(stmt)

    # ── drop resolution ───────────────────────────────────────────────

    @staticmethod
    def _resolve_drops(route: Route) -> list[DropSpec]:
        specs: list[DropSpec] = []
        for conn in route.connections:
            for drop_def in conn.drops:
                name = f"drop_{len(specs)}"
                specs.append(DropSpec(conn=conn, drop=drop_def, alias=aliased(DropModel, name=name)))
        return specs

    # ── SELECT ────────────────────────────────────────────────────────

    def _build_select(self, drop_aliases: list[object]) -> Select:
        return select(*self._seg_aliases, *drop_aliases)

    # ── segment JOINs ─────────────────────────────────────────────────

    def _join_segments(self, stmt: Select, container_ids: list[int]) -> Select:
        route = self._route
        stmt = self._join_segment_prices(
            stmt, self._seg_aliases[0], self._price_aliases[0],
            route.segments[0], container_ids,
        )

        for i in range(1, len(route.segments)):
            conn = route.connections[i - 1]
            from_alias = self._alias_map[id(conn.from_seg)]
            to_alias = self._alias_map[id(conn.to_seg)]
            stmt = stmt.join(self._seg_aliases[i], conn.build_condition(from_alias, to_alias))
            stmt = self._join_segment_prices(
                stmt, self._seg_aliases[i], self._price_aliases[i],
                route.segments[i], container_ids,
            )

        return stmt

    @staticmethod
    def _join_segment_prices(
        stmt: Select,
        seg_alias: object,
        price_alias: object,
        seg_def: object,
        container_ids: list[int],
    ) -> Select:
        cids = getattr(seg_def, "_container_ids", None) or container_ids
        return stmt.join(
            price_alias,
            and_(
                seg_alias.id == price_alias.route_id,  # type: ignore[attr-defined]
                price_alias.container_id.in_(cids),  # type: ignore[attr-defined]
            ),
        )

    # ── drop JOINs + WHERE ────────────────────────────────────────────

    def _join_drops(self, stmt: Select, date: datetime.date) -> Select:
        for spec in self._drop_specs:
            stmt = self._join_single_drop(stmt, spec, date)
        return stmt

    def _join_single_drop(self, stmt: Select, spec: DropSpec, date: datetime.date) -> Select:
        from_alias = self._alias_map[id(spec.conn.from_seg)]  # type: ignore[attr-defined]
        to_alias = self._alias_map[id(spec.conn.to_seg)]  # type: ignore[attr-defined]
        from_price = self._price_map[id(spec.conn.from_seg)]  # type: ignore[attr-defined]
        to_price = self._price_map[id(spec.conn.to_seg)]  # type: ignore[attr-defined]
        drop_alias = spec.alias

        rules_cond = spec.drop.build_condition(from_alias, to_alias, drop_alias, from_price, to_price, date)
        join_cond, where_cond = spec.drop.build_join(from_alias, drop_alias, rules_cond)

        if spec.drop.required:
            stmt = stmt.join(drop_alias, join_cond)
        else:
            stmt = stmt.outerjoin(drop_alias, join_cond)

        if where_cond is not None:
            stmt = stmt.where(where_cond)

        return stmt

    # ── filters ───────────────────────────────────────────────────────

    def _apply_filters(
        self,
        stmt: Select,
        dep_id: int,
        dest_id: int,
        date: datetime.date,
    ) -> Select:
        for seg_def, alias in zip(self._route.segments, self._seg_aliases):
            stmt = stmt.where(alias.type == seg_def.route_type)  # type: ignore[attr-defined]
            for f in seg_def._filters:
                stmt = stmt.where(f.to_sql(alias, date, dep_id, dest_id))
        return stmt

    # ── ordering ──────────────────────────────────────────────────────

    def _apply_ordering(self, stmt: Select) -> Select:
        return stmt.order_by(*[desc(a.effective_to) for a in self._seg_aliases])  # type: ignore[attr-defined]

    # ── eager loading ─────────────────────────────────────────────────

    def _apply_eager_loading(self, stmt: Select) -> Select:
        options = []
        for seg_alias, price_alias, svc_alias in zip(
            self._seg_aliases, self._price_aliases, self._svc_aliases,
        ):
            options.extend([
                joinedload(seg_alias.start_point),  # type: ignore[attr-defined]
                joinedload(seg_alias.end_point),  # type: ignore[attr-defined]
                joinedload(seg_alias.company),  # type: ignore[attr-defined]
                contains_eager(
                    seg_alias.prices, alias=price_alias,  # type: ignore[attr-defined]
                ).joinedload(PriceModel.container),
                selectinload(
                    seg_alias.services.of_type(svc_alias),  # type: ignore[attr-defined]
                ).joinedload(svc_alias.service),  # type: ignore[attr-defined]
            ])
        return stmt.options(*options)
