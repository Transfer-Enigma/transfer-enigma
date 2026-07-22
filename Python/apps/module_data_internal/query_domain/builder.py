import datetime
from collections import deque
from collections.abc import Iterable
from typing import Any, Self

from module_data_internal.query_domain.drop_off import DropOff
from module_data_internal.query_domain.expr import ColumnRef, Condition
from module_data_internal.query_domain.expr import Connector as ExprConnector
from module_data_internal.query_domain.expr import PriceRef
from module_data_internal.query_domain.segment import Segment
from module_data_internal.schemas import DropModel
from module_shared.schemas.route import PriceModel, RouteModel, ServicePriceModel
from sqlalchemy import Select, and_, desc, not_, or_, select, true
from sqlalchemy.orm import aliased, contains_eager, joinedload, selectinload


class RouteBuilder:
    class Connector:
        and_ = staticmethod(ExprConnector.and_)
        or_ = staticmethod(ExprConnector.or_)

    def __init__(self, current_date: datetime.date) -> None:
        self._date = current_date

        self._container_ids: list[int] | None = None
        self._start_point_id: int | None = None
        self._start_point_ids: list[int] | None = None
        self._end_point_id: int | None = None
        self._end_point_ids: list[int] | None = None
        self._company_ids: list[int] | None = None

        self._segments: deque[Segment] = deque()
        self._connections: deque[list[Condition]] = deque()
        self._drops: list[tuple[DropOff, list[Condition]]] = []
        self._global_conditions: list[Condition] = []

    # -- setters -----------------------------------------------------------

    def set_containers(self, ids: list[int]) -> Self:
        self._container_ids = list(ids)
        return self

    def set_container(self, _id: int) -> Self:
        self._container_ids = [_id]
        return self

    def set_start_point(self, _id: int) -> Self:
        self._start_point_id = _id
        return self

    def set_start_points(self, ids: list[int]) -> Self:
        self._start_point_ids = list(ids)
        return self

    def set_end_point(self, _id: int) -> Self:
        self._end_point_id = _id
        return self

    def set_end_points(self, ids: list[int]) -> Self:
        self._end_point_ids = list(ids)
        return self

    def set_companies(self, ids: list[int]) -> Self:
        self._company_ids = list(ids)
        return self

    def set_company(self, _id: int) -> Self:
        self._company_ids = [_id]
        return self

    # -- segment management -----------------------------------------------

    def add_segment(
        self,
        segment: Segment,
        *,
        conditions: Condition | Iterable[Condition] = (),
    ) -> Self:
        if isinstance(conditions, Condition):
            conds = [conditions]
        else:
            conds = list(conditions)

        if self._segments:
            self._connections.append(conds)
        else:
            self._global_conditions.extend(conds)

        self._segments.append(segment)
        return self

    def prepend_segment(
        self,
        segment: Segment,
        *,
        conditions: Condition | Iterable[Condition] = (),
    ) -> Self:
        if isinstance(conditions, Condition):
            conds = [conditions]
        else:
            conds = list(conditions)
        self._segments.appendleft(segment)
        if len(self._segments) > 1:
            self._connections.appendleft(conds)
        return self

    def get_first_segment(self):
        return self._segments[0]

    def get_last_segment(self):
        return self._segments[-1]

    # -- global conditions & drops -----------------------------------------

    def add_condition(self, condition: Condition) -> Self:
        self._global_conditions.append(condition)
        return self

    def add_drop_off(
        self,
        drop: DropOff,
        *,
        conditions: Condition | Iterable[Condition] | None = None,
    ) -> Self:
        if conditions is None:
            conds: list[Condition] = []
        elif isinstance(conditions, Condition):
            conds = [conditions]
        else:
            conds = list(conditions)
        self._drops.append((drop, conds))
        return self

    def copy(self) -> RouteBuilder:
        b = RouteBuilder.__new__(RouteBuilder)
        b._date = self._date
        b._container_ids = self._container_ids
        b._start_point_id = self._start_point_id
        b._start_point_ids = self._start_point_ids
        b._end_point_id = self._end_point_id
        b._end_point_ids = self._end_point_ids
        b._company_ids = self._company_ids
        b._segments = deque(self._segments)
        b._connections = deque(self._connections)
        b._drops = list(self._drops)
        b._global_conditions = list(self._global_conditions)
        return b

    # -- compilation -------------------------------------------------------

    def _resolve_column(self, ref: ColumnRef | PriceRef, alias_map: dict[int, Any]) -> Any:
        if isinstance(ref, PriceRef):
            price_ref = ref
            column_name = "container_id"
        elif isinstance(ref, ColumnRef) and isinstance(ref.owner, PriceRef):
            price_ref = ref.owner
            column_name = ref.column_name
        else:
            alias = alias_map.get(id(ref.owner))
            if alias is None:
                raise KeyError(f"No alias for {type(ref.owner).__name__}")
            return getattr(alias, ref.column_name)

        for i, seg in enumerate(self._segments):
            if seg is price_ref.segment:
                return getattr(self._price_aliases[i], column_name)
        raise KeyError("Segment in PriceRef not found in builder segments")

    def _resolve(self, cond: Condition, alias_map: dict[int, Any]) -> Any:  # noqa: C901
        if cond.op == "eq":
            left = self._resolve_column(cond.left, alias_map)  # type: ignore[arg-type]
            if isinstance(cond.right, ColumnRef):
                right = self._resolve_column(cond.right, alias_map)
            else:
                right = cond.right
            return left == right
        if cond.op == "not":
            if isinstance(cond.operand, Condition):
                inner = self._resolve(cond.operand, alias_map)
                return not_(inner)
            return not_(self._resolve_column(cond.operand, alias_map))  # type: ignore[arg-type]
        if cond.op == "is_not_null":
            return self._resolve_column(cond.operand, alias_map).isnot(None)  # type: ignore[arg-type]
        if cond.op == "is_null":
            return self._resolve_column(cond.operand, alias_map).is_(None)  # type: ignore[arg-type]
        if cond.op == "in":
            col = self._resolve_column(cond.left, alias_map)  # type: ignore[arg-type]
            return col.in_(cond.right)
        if cond.op == "lte":
            col = self._resolve_column(cond.left, alias_map)  # type: ignore[arg-type]
            return col <= cond.right
        if cond.op == "gte":
            col = self._resolve_column(cond.left, alias_map)  # type: ignore[arg-type]
            return col >= cond.right
        if cond.op == "and":
            return and_(*[self._resolve(c, alias_map) for c in (cond.operands or [])])
        if cond.op == "or":
            return or_(*[self._resolve(c, alias_map) for c in (cond.operands or [])])
        raise ValueError(f"Unknown condition op: {cond.op}")

    def build(self) -> Select:  # noqa: C901
        n = len(self._segments)
        if n == 0:
            raise RuntimeError("No segments defined")

        seg_aliases: list[Any] = [aliased(RouteModel, name=f"seg_{i}") for i in range(n)]
        price_aliases: list[Any] = [aliased(PriceModel, name=f"price_{i}") for i in range(n)]
        svc_aliases: list[Any] = [aliased(ServicePriceModel, name=f"svc_{i}") for i in range(n)]
        drop_aliases: list[Any] = [aliased(DropModel, name=f"drop_{i}") for i in range(len(self._drops))]

        alias_map: dict[int, Any] = {}
        for seg, alias in zip(self._segments, seg_aliases):
            alias_map[id(seg)] = alias
        for (drop, _), alias in zip(self._drops, drop_aliases):
            alias_map[id(drop)] = alias

        self._price_aliases = price_aliases

        stmt: Select = select(*seg_aliases, *drop_aliases).select_from(seg_aliases[0])

        # Price JOIN for first segment
        stmt = stmt.join(
            price_aliases[0],
            and_(
                seg_aliases[0].id == price_aliases[0].route_id,
                price_aliases[0].container_id.in_(self._container_ids),
            ) if self._container_ids else (
                seg_aliases[0].id == price_aliases[0].route_id
            ),
        )

        # JOIN additional segments
        connections_iter = iter(self._connections)
        for i in range(1, n):
            edge_conds = next(connections_iter)
            resolved = [self._resolve(c, alias_map) for c in edge_conds]
            join_on = and_(*resolved) if resolved else true()
            stmt = stmt.join(seg_aliases[i], join_on)

            stmt = stmt.join(
                price_aliases[i],
                and_(
                    seg_aliases[i].id == price_aliases[i].route_id,
                    price_aliases[i].container_id.in_(self._container_ids),
                ) if self._container_ids else (
                    seg_aliases[i].id == price_aliases[i].route_id
                ),
            )

        # Drop LEFT JOINs
        for (_, drop_conds), drop_alias in zip(self._drops, drop_aliases):
            resolved = [self._resolve(c, alias_map) for c in drop_conds]
            join_on = and_(*resolved) if resolved else true()
            stmt = stmt.outerjoin(drop_alias, join_on)

        # WHERE
        where_conds: list[Any] = []
        for i, seg in enumerate(self._segments):
            alias = seg_aliases[i]
            if seg._type_filter is not None:
                where_conds.append(alias.type == seg._type_filter.value)
            where_conds.append(alias.effective_from <= self._date)
            where_conds.append(alias.effective_to >= self._date)

            if i == 0:
                if self._start_point_id is not None:
                    where_conds.append(alias.start_point_id == self._start_point_id)
                elif self._start_point_ids is not None:
                    where_conds.append(alias.start_point_id.in_(self._start_point_ids))
            if i == n - 1:
                if self._end_point_id is not None:
                    where_conds.append(alias.end_point_id == self._end_point_id)
                elif self._end_point_ids is not None:
                    where_conds.append(alias.end_point_id.in_(self._end_point_ids))

            if self._company_ids is not None:
                where_conds.append(alias.company_id.in_(self._company_ids))

        for cond in self._global_conditions:
            where_conds.append(self._resolve(cond, alias_map))

        if where_conds:
            stmt = stmt.where(and_(*where_conds))

        # ORDER BY
        stmt = stmt.order_by(*[desc(a.effective_to) for a in seg_aliases])

        # Eager loading
        options: list[Any] = []
        for i, (seg_alias, price_alias) in enumerate(zip(seg_aliases, price_aliases)):
            options.extend([
                joinedload(seg_alias.start_point),
                joinedload(seg_alias.end_point),
                joinedload(seg_alias.company),
                contains_eager(seg_alias.prices, alias=price_alias).joinedload(PriceModel.container),
                selectinload(
                    seg_alias.services.of_type(svc_aliases[i]),
                ).joinedload(svc_aliases[i].service),  # type: ignore[arg-type]
            ])
        stmt = stmt.options(*options)

        return stmt
