import pandas as pd
from backend_admin.service.routes_loading.uid import (
    extract_uids,
    natural_uid_for_dropp_values,
    natural_uid_for_route_values,
    plan_uid_updates,
)
from backend_admin.service.routes_loading.uid_sheet import (
    GsheetsUidGateway,
    col_to_letter,
    ensure_sheet_uids,
)
from backend_admin.service.routes_loading.validation import validate_frames

from .fixtures.frames import (
    clean_dropp_row,
    clean_sea_row,
    make_fc,
    make_frame,
    make_points_frame,
    make_services_frame,
    make_snapshot,
)


class FakeSpreadsheet:
    def __init__(self):
        self.updates = []

    def batch_update(self, body):
        self.updates.append(body)


class FakeWorksheet:
    def __init__(self, values, sheet_id=123):
        self._values = [list(row) for row in values]
        self.id = sheet_id
        self.spreadsheet = FakeSpreadsheet()
        self.updates = []

    def get_all_values(self):
        return [list(row) for row in self._values]

    def update(self, cell_range, values):
        self.updates.append((cell_range, values))


class TestNaturalUid:
    def test_stable_across_price_change(self):
        base = {
            "type": "SEA", "company": "FESCO", "start_point": "Vladivostok",
            "end_point": "Moscow", "dropp_off_point": None,
            "effective_from": "2026-01-01", "effective_to": "2026-12-31",
            "container_shipment_terms": "FOR", "container_transfer_terms": "FILO",
            "container_owner": "COC", "is_through": True,
        }
        assert natural_uid_for_route_values(base) == natural_uid_for_route_values(dict(base))

    def test_differs_by_natural_key(self):
        base = {
            "type": "SEA", "company": "FESCO", "start_point": "Vladivostok",
            "end_point": "Moscow", "dropp_off_point": None,
            "effective_from": "2026-01-01", "effective_to": "2026-12-31",
            "container_shipment_terms": "FOR", "container_transfer_terms": "FILO",
            "container_owner": "COC", "is_through": True,
        }
        assert natural_uid_for_route_values(base) != natural_uid_for_route_values(
            {**base, "company": "OTHER"},
        )
        assert natural_uid_for_route_values(base) != natural_uid_for_route_values(
            {**base, "type": "RAIL"},
        )

    def test_case_insensitive(self):
        values = {
            "start_point": "Vladivostok", "end_point": "Moscow", "company": "FESCO",
            "effective_from": "2026-01-01", "effective_to": "2026-12-31",
        }
        assert natural_uid_for_dropp_values(values) == natural_uid_for_dropp_values({
            "start_point": "  vladivostok ", "end_point": "MOSCOW", "company": "fesco",
            "effective_from": "2026-01-01", "effective_to": "2026-12-31",
        })


class TestExtractAndPlan:
    def test_extract_skips_blanks(self):
        df = pd.DataFrame({"__uid": ["abc", None, "  ", "def"]})
        assert extract_uids(df, "__uid") == {0: "abc", 3: "def"}

    def test_extract_missing_column(self):
        df = pd.DataFrame({"a": [1]})
        assert extract_uids(df, "__uid") == {}
        assert extract_uids(None, "__uid") == {}

    def test_plan_returns_only_missing(self):
        assert plan_uid_updates({2: "a", 3: "b"}, {2: "a", 3: "b", 4: "c"}) == {4: "c"}
        assert plan_uid_updates(None, {2: "a"}) == {2: "a"}
        assert plan_uid_updates({2: "a"}, {}) == {}


class TestColToLetter:
    def test_letters(self):
        assert col_to_letter(0) == "A"
        assert col_to_letter(25) == "Z"
        assert col_to_letter(26) == "AA"
        assert col_to_letter(27) == "AB"


class TestGateway:
    def test_append_path_writes_column_and_hides(self):
        ws = FakeWorksheet([["city", "country"], ["V", "R"], ["M", "R"]])
        gateway = GsheetsUidGateway(ws)

        existing, data_rows = gateway.read_uids("__uid")

        assert existing is None
        assert data_rows == 2
        assert gateway.column_position("__uid") is None
        assert gateway.append_uid_column("__uid", ["u1", "u2"]) == 2
        assert ws.updates == [("C1:C3", [["__uid"], ["u1"], ["u2"]])]
        assert ws.spreadsheet.updates != []

    def test_fill_path_updates_only_missing(self):
        ws = FakeWorksheet([["city", "__uid"], ["V", "u1"], ["M", ""]])
        gateway = GsheetsUidGateway(ws)

        existing, _ = gateway.read_uids("__uid")

        assert existing == {2: "u1"}
        assert gateway.column_position("__uid") == 1
        assert gateway.fill_missing_uids(1, {3: "u2"}) == 1
        assert ws.updates == [("B3", [["u2"]])]


class TestEnsureSheetUids:
    def test_appends_for_new_column(self):
        ws = FakeWorksheet([["city"], ["V"], ["M"]])
        written = ensure_sheet_uids(
            {"ws": ws}, {"sea": ("SEA", "ws")},
            {("SEA", 0): "u1", ("SEA", 1): "u2"}, "__uid",
        )
        assert written == 2
        assert ws.updates[0][0] == "B1:B3"

    def test_skips_unknown_worksheets(self):
        written = ensure_sheet_uids({}, {"sea": ("SEA", "ws")}, {("SEA", 0): "u1"}, "__uid")
        assert written == 0

    def test_skips_rows_without_uids(self):
        ws = FakeWorksheet([["city"], ["V"]])
        written = ensure_sheet_uids({"ws": ws}, {"sea": ("SEA", "ws")}, {}, "__uid")
        assert written == 0
        assert ws.updates == []


class TestValidateRowUids:
    def _frames(self, fc):
        return {
            "sea": make_frame(fc, [clean_sea_row(fc)]),
            "rail": None,
            "truck": None,
            "dropp": make_frame(fc, [clean_dropp_row(fc)]),
            "services": make_services_frame(fc),
            "points": make_points_frame(),
        }

    def test_computed_for_all_rows(self):
        fc = make_fc()
        frames = self._frames(fc)
        validated = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(),
        )
        assert set(validated.row_uids) == {("SEA", 0), ("DROPP", 0)}
        assert validated.row_uids[("SEA", 0)] != validated.row_uids[("DROPP", 0)]

    def test_existing_uid_preferred(self):
        fc = make_fc()
        frames = self._frames(fc)
        frames["sea"]["__uid"] = ["keep-me"]
        validated = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(), uid_column="__uid",
        )
        assert validated.row_uids[("SEA", 0)] == "keep-me"

    def test_custom_uid_column(self):
        fc = make_fc()
        frames = self._frames(fc)
        frames["dropp"]["ref"] = ["d1"]
        validated = validate_frames(
            frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
            frames["services"], frames["points"], fc, make_snapshot(), uid_column="ref",
        )
        assert validated.row_uids[("DROPP", 0)] == "d1"
        assert ("SEA", 0) in validated.row_uids
