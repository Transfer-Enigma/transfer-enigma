import pytest
from backend_admin.models.upoader_fields_config import UploaderFieldsConfig
from backend_admin.service.routes_loading.error_reporting import (
    parse_all_warning_types,
    parse_error,
    parse_warning,
)
from backend_admin.service.routes_loading.errors import (
    CompanyNotFoundException,
    InvalidDroppRow,
    InvalidRouteConditionException,
    InvalidRouteTypeException,
    LoadingErrorException,
    NoPriceInRouteException,
    PointNotFoundException,
)
from backend_admin.service.routes_loading.sync_errors import (
    SyncError,
    SyncErrorCode,
    get_message,
    gsheets_unavailable_error,
    load_locale,
    points_sheet_nan_error,
    unexpected_error,
    ws_not_found_error,
)
from module_shared.schemas.route import RouteType


def _fields_config(**overrides):
    data = {
        name: name
        for name, field in UploaderFieldsConfig.model_fields.items()
        if field.is_required()
    }
    data["effective_from"] = "effective_from"
    data["effective_to"] = "effective_to"
    data.update(overrides)
    return UploaderFieldsConfig(**data)


class TestLocaleCoverage:
    def test_every_code_has_ru_template(self):
        for code in SyncErrorCode:
            assert get_message(code, sheet="S", row=1, count=1, key="K", value="V",
                               field="F", col_from="A", col_to="B", uid="U",
                               condition="C", type="T", detail="D") != ""

    def test_unknown_code_raises(self):
        with pytest.raises(KeyError):
            get_message("NO_SUCH_CODE", sheet="S")

    def test_templates_use_placeholders(self):
        assert "{key}" in load_locale("ru")["POINT_NOT_FOUND"]
        assert "{uid}" in load_locale("ru")["UID_NOT_IN_DB"]
        assert "{row}" in load_locale("ru")["DUPLICATE_ROW"]


class TestSyncErrorSchema:
    def test_model_dump_has_universal_fields(self):
        entry = SyncError(document="doc", sheet="S", row=3, cell="B3",
                          code=SyncErrorCode.NO_PRICE, message="m", severity="error")
        assert entry.model_dump() == {
            "document": "doc",
            "sheet": "S",
            "row": 3,
            "cell": "B3",
            "code": "NO_PRICE",
            "message": "m",
            "severity": "error",
        }

    def test_optional_fields_default_to_none(self):
        entry = SyncError(code=SyncErrorCode.UNKNOWN, message="m")
        assert entry.document is None and entry.sheet is None
        assert entry.row is None and entry.cell is None
        assert entry.severity == "error"


class TestParseError:
    @pytest.mark.parametrize(("exc", "code"), [
        (InvalidRouteConditionException("FOB"), SyncErrorCode.BAD_ENUM_VALUE),
        (PointNotFoundException("MSK"), SyncErrorCode.POINT_NOT_FOUND),
        (CompanyNotFoundException("FESCO"), SyncErrorCode.COMPANY_NOT_FOUND),
        (InvalidRouteTypeException("AVIA"), SyncErrorCode.BAD_ENUM_VALUE),
        (NoPriceInRouteException(), SyncErrorCode.NO_PRICE),
        (InvalidDroppRow("bad"), SyncErrorCode.DROPP_ROW_INVALID),
        (LoadingErrorException("boom"), SyncErrorCode.UNKNOWN),
    ])
    def test_exception_to_code(self, exc, code):
        parsed = parse_error(exc, 0, RouteType.SEA, document="doc")
        assert parsed["code"] == code.value
        assert parsed["sheet"] == "МОРЕ"
        assert parsed["row"] == 2
        assert parsed["severity"] == "error"
        assert parsed["document"] == "doc"
        assert parsed["message"] == parsed["error"]
        assert parsed["error"] != ""

    def test_sheet_labels(self):
        assert parse_error(NoPriceInRouteException(), 0, RouteType.RAIL)["sheet"] == "ЖД"
        assert parse_error(NoPriceInRouteException(), 0, None)["sheet"] == "ДРОПП"
        assert parse_error(NoPriceInRouteException(), 0, "SOMETHING")["sheet"] == "Неизвестный"

    def test_message_matches_locale_template(self):
        parsed = parse_error(PointNotFoundException("MSK"), 3, RouteType.SEA)
        assert parsed["message"] == get_message(
            SyncErrorCode.POINT_NOT_FOUND, sheet="МОРЕ", row=5, key="MSK",
        )


class TestParseWarning:
    def test_missing_cells_keeps_rows_list(self):
        fc = _fields_config()
        value = ({"row_index": 0, "skipped_columns": ["A", "B"]}, {"row_index": 4, "skipped_columns": ["C"]})
        parsed = parse_warning("MissingRoutesDataException", value, "МОРЕ", fc, document="doc")
        assert parsed["code"] == SyncErrorCode.REQUIRED_CELL_EMPTY.value
        assert parsed["severity"] == "warning"
        assert parsed["sheet"] == "МОРЕ"
        assert parsed["document"] == "doc"
        assert parsed["rows_list"] == [
            {"error": parsed["rows_list"][0]["error"], "row_number": 2, "columns": ["A", "B"]},
            {"error": parsed["rows_list"][1]["error"], "row_number": 6, "columns": ["C"]},
        ]
        assert parsed["error"] != ""

    def test_bad_date_format_row_numbers(self):
        fc = _fields_config(effective_from="FROM", effective_to="TO")
        parsed = parse_warning("UnsupportedDateFormat", (0, 2), "ЖД", fc)
        assert parsed["code"] == SyncErrorCode.BAD_DATE_FORMAT.value
        assert parsed["row_numbers"] == [2, 4]
        assert "FROM/TO" in parsed["error"]

    def test_unknown_warning_key(self):
        parsed = parse_warning("SomeFutureKey", (1,), "МОРЕ", _fields_config())
        assert parsed["code"] == SyncErrorCode.UNKNOWN.value
        assert parsed["severity"] == "warning"
        assert parsed["row_numbers"] == [3]


class TestParseAllWarningTypes:
    def test_deduplicates_identical_errors(self):
        warnings = [
            (NoPriceInRouteException(), 0, RouteType.SEA),
            (NoPriceInRouteException(), 0, RouteType.SEA),
            (NoPriceInRouteException(), 1, RouteType.SEA),
        ]
        parsed = parse_all_warning_types(warnings, _fields_config())
        assert [entry["row"] for entry in parsed] == [2, 3]

    def test_mixes_errors_and_warnings(self):
        warnings = [
            (NoPriceInRouteException(), 0, RouteType.SEA),
            ("MissingRoutesDataException",
             ({"row_index": 0, "skipped_columns": ["A"]},), "МОРЕ"),
        ]
        parsed = parse_all_warning_types(warnings, _fields_config())
        assert [entry["code"] for entry in parsed] == ["NO_PRICE", "REQUIRED_CELL_EMPTY"]
        assert [entry["severity"] for entry in parsed] == ["error", "warning"]

    def test_document_propagates(self):
        warnings = [(NoPriceInRouteException(), 0, RouteType.SEA)]
        parsed = parse_all_warning_types(warnings, _fields_config(), document="http://doc")
        assert parsed[0]["document"] == "http://doc"


class TestHttpHelpers:
    def test_gsheets_unavailable(self):
        exc = gsheets_unavailable_error(ConnectionError("down"), document="doc").detail
        assert exc["code"] == SyncErrorCode.GSHEETS_UNAVAILABLE.value
        assert exc["document"] == "doc"
        assert exc["type"] == "ConnectionError"

    def test_ws_not_found(self):
        exc = ws_not_found_error(ValueError("no ws"), sheet="МОРЕ").detail
        assert exc["code"] == SyncErrorCode.WS_NOT_FOUND.value
        assert exc["sheet"] == "МОРЕ"

    def test_unexpected(self):
        exc = unexpected_error(RuntimeError("boom")).detail
        assert exc["code"] == SyncErrorCode.UNKNOWN.value
        assert exc["type"] == "RuntimeError"

    def test_points_sheet_nan_keeps_legacy_fields(self):
        exc = points_sheet_nan_error([2, 5], sheet="Точки").detail
        assert exc["code"] == SyncErrorCode.POINTS_SHEET_NAN.value
        assert exc["sheet"] == "Точки"
        assert exc["row_numbers"] == [2, 5]
        assert exc["error"] != ""

    def test_status_codes(self):
        assert gsheets_unavailable_error(Exception()).status_code == 503
        assert ws_not_found_error(Exception()).status_code == 503
        assert unexpected_error(Exception()).status_code == 500
        assert points_sheet_nan_error([]).status_code == 400
