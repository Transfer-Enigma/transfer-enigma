import pandas as pd
from backend_admin.service.routes_loading.fixes import apply_fixes
from backend_admin.service.routes_loading.validation import validate_frames

from .fixtures.frames import (
    clean_sea_row,
    make_fc,
    make_frame,
    make_points_frame,
    make_services_frame,
    make_snapshot,
)


class TestApplyFixes:
    def test_trims_and_uppercases(self):
        fc = make_fc()
        frames = {
            "sea": make_frame(fc, [clean_sea_row(fc, **{fc.company: "  fesco  "})]),
            "rail": None,
            "truck": None,
            "dropp": None,
            "services": None,
            "points": None,
        }
        fixed, fixes = apply_fixes(frames, fc)

        assert fixed["sea"][fc.company].tolist() == ["FESCO"]
        assert fixes == [{
            "sheet": "sea",
            "row": 2,
            "column": fc.company,
            "old": "  fesco  ",
            "new": "FESCO",
        }]
        assert frames["sea"][fc.company].tolist() == ["  fesco  "]

    def test_normalizes_dates(self):
        fc = make_fc()
        frames = {
            "sea": make_frame(fc, [clean_sea_row(fc, **{fc.effective_from: "01-Jan-26"})]),
            "rail": None,
            "truck": None,
            "dropp": None,
            "services": None,
            "points": None,
        }
        fixed, fixes = apply_fixes(frames, fc)

        assert fixed["sea"][fc.effective_from].tolist() == ["2026-01-01"]
        assert fixes[0]["column"] == fc.effective_from
        assert fixes[0]["old"] == "01-Jan-26"
        assert fixes[0]["new"] == "2026-01-01"

    def test_leaves_clean_and_missing_untouched(self):
        fc = make_fc()
        frames = {
            "sea": make_frame(fc, [clean_sea_row(fc, **{fc.company: "FESCO"})]),
            "rail": None,
            "truck": None,
            "dropp": None,
            "services": None,
            "points": None,
        }
        fixed, fixes = apply_fixes(frames, fc)

        assert fixes == []
        assert fixed["sea"].equals(frames["sea"])

    def test_skips_non_string_cells(self):
        fc = make_fc()
        frames = {
            "sea": make_frame(fc, [clean_sea_row(fc, **{fc.sea_20dc: 100.0})]),
            "rail": None,
            "truck": None,
            "dropp": None,
            "services": None,
            "points": None,
        }
        _, fixes = apply_fixes(frames, fc)
        assert all(fix["column"] != fc.sea_20dc for fix in fixes)

    def test_points_frame_trimmed_without_case_change(self):
        fc = make_fc()
        points = pd.DataFrame([{
            "city": "  Vladivostok ",
            "country": "RU",
            "RU_city": "Владивосток",
            "RU_country": "РФ",
        }])
        fixed, fixes = apply_fixes({"points": points}, fc)

        assert fixed["points"]["city"].tolist() == ["Vladivostok"]
        assert fixes[0]["sheet"] == "points"


class TestFixThenValidate:
    def test_fixed_frames_validate_clean(self):
        fc = make_fc()
        frames = {
            "sea": make_frame(fc, [clean_sea_row(fc, **{fc.company: "fesco "})]),
            "rail": None,
            "truck": None,
            "dropp": None,
            "services": make_services_frame(fc),
            "points": make_points_frame(),
        }
        fixed, fixes = apply_fixes(frames, fc)
        assert fixes != []

        validated = validate_frames(
            fixed["sea"], fixed["rail"], fixed["truck"], fixed["dropp"],
            fixed["services"], fixed["points"], fc, make_snapshot(),
        )
        assert validated.report.errors == []
