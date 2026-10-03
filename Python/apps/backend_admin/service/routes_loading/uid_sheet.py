from .uid import plan_uid_updates


def col_to_letter(index: int) -> str:
    letters = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


class GsheetsUidGateway:
    def __init__(self, worksheet):
        self.worksheet = worksheet

    def read_uids(self, uid_column: str) -> tuple[dict[int, str] | None, int]:
        values = self.worksheet.get_all_values()
        if not values:
            return None, 0
        header = values[0]
        if uid_column not in header:
            return None, len(values) - 1
        position = header.index(uid_column)
        existing = {}
        for sheet_row in range(2, len(values) + 1):
            cell = values[sheet_row - 1][position] if position < len(values[sheet_row - 1]) else ""
            if cell and str(cell).strip():
                existing[sheet_row] = str(cell).strip()
        return existing, len(values) - 1

    def header(self) -> list[str]:
        values = self.worksheet.get_all_values()
        return list(values[0]) if values else []

    def column_position(self, uid_column: str) -> int | None:
        header = self.header()
        if not header or uid_column not in header:
            return None
        return header.index(uid_column)

    def append_uid_column(self, uid_column: str, ordered_uids: list[str]) -> int:
        values = self.worksheet.get_all_values()
        position = len(values[0]) if values else 0
        letter = col_to_letter(position)
        payload = [[uid_column], *[[uid] for uid in ordered_uids]]
        self.worksheet.update(f"{letter}1:{letter}{len(payload)}", payload)
        self.hide_column(position)
        return len(ordered_uids)

    def fill_missing_uids(self, position: int, updates: dict[int, str]) -> int:
        letter = col_to_letter(position)
        for sheet_row, uid in sorted(updates.items()):
            self.worksheet.update(f"{letter}{sheet_row}", [[uid]])
        return len(updates)

    def write_cells(self, updates: list[tuple[int, int, object]]) -> int:
        for sheet_row, position, value in updates:
            self.worksheet.update(f"{col_to_letter(position)}{sheet_row}", [[value if value is not None else ""]])
        return len(updates)

    def highlight_cells(self, cells: list[tuple[int, int]], red: float = 1.0,
                        green: float = 0.85, blue: float = 0.85) -> int:
        if not cells:
            return 0
        self.worksheet.spreadsheet.batch_update({
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": sheet_row - 1,
                            "endRowIndex": sheet_row,
                            "startColumnIndex": position,
                            "endColumnIndex": position + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": red, "green": green, "blue": blue},
                            },
                        },
                        "fields": "userEnteredFormat.backgroundColor",
                    },
                }
                for sheet_row, position in cells
            ],
        })
        return len(cells)

    def hide_column(self, position: int) -> None:
        spreadsheet = self.worksheet.spreadsheet
        spreadsheet.batch_update({
            "requests": [{
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": position,
                        "endIndex": position + 1,
                    },
                    "properties": {"hiddenByUser": True},
                    "fields": "hiddenByUser",
                },
            }],
        })


def ensure_sheet_uids(worksheets: dict, key_scope_names: dict[str, tuple[str, str | None]],
                      row_uids: dict[tuple[str, int], str], uid_column: str) -> int:
    written = 0
    for _key, (scope, ws_name) in key_scope_names.items():
        if not ws_name or ws_name not in worksheets:
            continue
        gateway = GsheetsUidGateway(worksheets[ws_name])
        existing, data_rows = gateway.read_uids(uid_column)
        computed = {
            orig_idx + 2: uid
            for (row_scope, orig_idx), uid in row_uids.items()
            if row_scope == scope
        }
        if not computed:
            continue
        if existing is None:
            ordered = [computed.get(sheet_row, "") for sheet_row in range(2, data_rows + 2)]
            written += gateway.append_uid_column(uid_column, ordered)
        else:
            position = gateway.column_position(uid_column)
            if position is None:
                continue
            written += gateway.fill_missing_uids(position, plan_uid_updates(existing, computed))
    return written


def write_fix_cells(worksheets: dict, key_scope_names: dict[str, tuple[str, str | None]],
                    fixes: list[dict]) -> int:
    written = 0
    by_key: dict[str, list[dict]] = {}
    for fix in fixes:
        by_key.setdefault(fix["sheet"], []).append(fix)
    for key, (_scope, ws_name) in key_scope_names.items():
        if not ws_name or ws_name not in worksheets or key not in by_key:
            continue
        gateway = GsheetsUidGateway(worksheets[ws_name])
        header = gateway.header()
        updates = []
        for fix in by_key[key]:
            if fix["column"] not in header:
                continue
            updates.append((fix["row"], header.index(fix["column"]), fix["new"]))
        written += gateway.write_cells(updates)
    return written


SHEET_SCOPES = {
    "МОРЕ": "SEA", "ЖД": "RAIL", "АВТО": "TRUCK", "ДРОПП": "DROPP",
    "SEA": "SEA", "RAIL": "RAIL", "TRUCK": "TRUCK", "DROPP": "DROPP",
}


def highlight_report_cells(worksheets: dict, key_scope_names: dict[str, tuple[str, str | None]],
                           findings: list) -> int:
    highlighted = 0
    by_scope: dict[str, list] = {}
    for finding in findings:
        scope = SHEET_SCOPES.get(finding.sheet or "")
        if scope:
            by_scope.setdefault(scope, []).append(finding)
    scope_to_ws = {scope: ws_name for _key, (scope, ws_name) in key_scope_names.items() if ws_name}
    for scope, scope_findings in by_scope.items():
        ws_name = scope_to_ws.get(scope)
        if not ws_name or ws_name not in worksheets:
            continue
        gateway = GsheetsUidGateway(worksheets[ws_name])
        header = gateway.header()
        cells = []
        for finding in scope_findings:
            if not finding.row or not finding.cell:
                continue
            for column in str(finding.cell).split(","):
                column = column.strip()
                if column in header:
                    cells.append((finding.row, header.index(column)))
        highlighted += gateway.highlight_cells(cells)
    return highlighted
