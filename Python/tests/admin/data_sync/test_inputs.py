from io import BytesIO

from fastapi import HTTPException

import pandas as pd
import pytest
from backend_admin.service.routes_loading.inputs import read_upload, select_upload_frames
from backend_admin.service.routes_loading.sync_errors import SyncErrorCode


def _xlsx_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


class TestReadUpload:
    def test_xlsx_returns_sheet_dict(self):
        data = _xlsx_bytes({
            "Море": pd.DataFrame([{"a": 1}]),
            "ЖД": pd.DataFrame([{"a": 2}]),
        })
        parsed = read_upload(data)
        assert set(parsed) == {"Море", "ЖД"}
        assert parsed["Море"]["a"].tolist() == [1]

    def test_csv_returns_single_frame(self):
        parsed = read_upload(_csv_bytes(pd.DataFrame([{"a": 1}, {"a": 2}])))
        assert not isinstance(parsed, dict)
        assert parsed["a"].tolist() == [1, 2]

    def test_empty_file_raises_coded_400(self):
        with pytest.raises(HTTPException) as exc_info:
            read_upload(b"")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == SyncErrorCode.BAD_INPUT_FORMAT.value


class TestSelectUploadFrames:
    def test_workbook_selects_by_name(self):
        parsed = {
            "Море": pd.DataFrame([{"a": 1}]),
            "ЖД": pd.DataFrame([{"a": 2}]),
        }
        frames = select_upload_frames(parsed, {"sea": "Море", "rail": "ЖД", "truck": None,
                                               "dropp": None, "services": None, "points": None})
        assert frames["sea"]["a"].tolist() == [1]
        assert frames["rail"]["a"].tolist() == [2]
        assert frames["truck"] is None

    def test_workbook_missing_sheet_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            select_upload_frames({"Море": pd.DataFrame()}, {"sea": "ЖД", "rail": None,
                                                            "truck": None, "dropp": None,
                                                            "services": None, "points": None})
        assert exc_info.value.status_code == 400

    def test_csv_goes_to_first_requested_sheet(self):
        frame = pd.DataFrame([{"a": 1}])
        frames = select_upload_frames(frame, {"sea": None, "rail": "Лист1", "truck": None,
                                              "dropp": None, "services": None, "points": None})
        assert frames["rail"] is frame
        assert frames["sea"] is None

    def test_all_keys_present(self):
        frames = select_upload_frames(pd.DataFrame(), {"sea": None, "rail": None, "truck": None,
                                                       "dropp": None, "services": None, "points": None})
        assert set(frames) == {"sea", "rail", "truck", "dropp", "services", "points"}
        assert all(value is None for value in frames.values())
