import json

from backend_admin.service.routes_loading.fixes import apply_fixes
from backend_admin.service.routes_loading.report import build_affected_rows
from backend_admin.service.routes_loading.sync_errors import SyncErrorCode
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


def _frames(fc):
    return {
        "sea": make_frame(fc, [clean_sea_row(fc)]),
        "rail": None,
        "truck": None,
        "dropp": make_frame(fc, [clean_dropp_row(fc)]),
        "services": make_services_frame(fc),
        "points": make_points_frame(),
    }


def _validate(fc, frames, snapshot=None, fix=False):
    if fix:
        frames, fixes = apply_fixes(frames, fc)
    else:
        fixes = []
    validated = validate_frames(
        frames["sea"], frames["rail"], frames["truck"], frames["dropp"],
        frames["services"], frames["points"], fc, snapshot or make_snapshot(),
    )
    return validated, fixes


class TestAffectedRows:
    def test_error_rows_carry_values_and_uid(self):
        fc = make_fc()
        frames = _frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.end_point: "Atlantis"})])
        validated, _ = _validate(fc, frames)

        affected = build_affected_rows(validated, [], fc)

        assert len(affected) == 1
        entry = affected[0]
        assert entry["scope"] == "SEA"
        assert entry["sheet"] == "МОРЕ"
        assert entry["row"] == 2
        assert entry["uid"] == validated.row_uids[("SEA", 0)]
        assert entry["values"][fc.end_point] == "Atlantis"
        assert entry["fixed"] is False
        assert [error["code"] for error in entry["errors"]] == ["POINT_NOT_FOUND"]
        assert entry["fixes"] == []
        assert entry["document"] is None

    def test_clean_rows_excluded(self):
        fc = make_fc()
        validated, _ = _validate(fc, _frames(fc))

        assert build_affected_rows(validated, [], fc) == []

    def test_fixed_rows_show_before_after(self):
        fc = make_fc()
        frames = _frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.company: "  fesco  "})])
        validated, fixes = _validate(fc, frames, fix=True)

        affected = build_affected_rows(validated, fixes, fc)
        by_scope = {entry["scope"]: entry for entry in affected}

        assert set(by_scope) == {"SEA", "DROPP"}
        assert by_scope["SEA"]["fixed"] is True
        assert by_scope["SEA"]["fixes"] == [fix for fix in fixes if fix["sheet"] == "sea"]
        assert by_scope["SEA"]["values"][fc.company] == "FESCO"
        assert by_scope["DROPP"]["fixed"] is True

    def test_dropp_rows_included(self):
        fc = make_fc()
        frames = _frames(fc)
        frames["dropp"] = make_frame(fc, [clean_dropp_row(fc, **{fc.end_point: "Atlantis"})])
        validated, _ = _validate(fc, frames)

        affected = build_affected_rows(validated, [], fc)
        scopes = {(entry["scope"], entry["row"]) for entry in affected}

        assert ("DROPP", 2) in scopes

    def test_serializable(self):
        fc = make_fc()
        frames = _frames(fc)
        frames["sea"] = make_frame(fc, [clean_sea_row(fc, **{fc.end_point: "Atlantis"})])
        validated, _ = _validate(fc, frames)

        affected = build_affected_rows(validated, [], fc)
        dumped = json.loads(json.dumps(affected))

        assert dumped[0]["errors"][0]["code"] == SyncErrorCode.POINT_NOT_FOUND.value
