from io import BytesIO
from typing import Protocol

import gspread
import pandas
from gspread_dataframe import get_as_dataframe
from shared.database import settings
from shared.resources import Resources


class DataDownloader(Protocol):
    def download_data(self, ws_name: str):
        ...


class GspreadDownloader:
    def __init__(self, gsheets_url: str):
        self.sources_gs = gspread.service_account(
            filename=Resources.get(settings.GOOGLE_SERVICE_ACCOUNT_RESOURCE_NAME, scope="backend_admin").path,
        ).open_by_url(gsheets_url)

    def download_data(self, ws_name: str):
        return get_as_dataframe(
            self.sources_gs.worksheet(ws_name),
            evaluate_formulas=True,
        )


class FileDownloader:
    def __init__(self, data_file: bytes):
        self.data_file = data_file

    def download_data(self, ws_name: str):
        return pandas.read_excel(BytesIO(self.data_file), ws_name)
