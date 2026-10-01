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

    def column_position(self, uid_column: str) -> int | None:
        values = self.worksheet.get_all_values()
        if not values or uid_column not in values[0]:
            return None
        return values[0].index(uid_column)

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
