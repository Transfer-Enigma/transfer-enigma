import io

import click
import gspread
import pandas as pd
from gspread_dataframe import get_as_dataframe

from .config import get_cli_settings


def _open_sheet():
    settings = get_cli_settings()
    gs_url = settings.GSHEETS_URL
    if not gs_url:
        raise click.ClickException(
            "GSHEETS_URL is not set.\n"
            "Set it via env var or in a .env file:\n"
            "  export GSHEETS_URL='https://docs.google.com/spreadsheets/d/...'\n"
            "  export GOOGLE_SERVICE_ACCOUNT_PATH='/path/to/service_account.json'"
        )

    sa_path = settings.GOOGLE_SERVICE_ACCOUNT_PATH
    if sa_path:
        gc = gspread.service_account(filename=sa_path)
    else:
        gc = gspread.service_account()

    return gc.open_by_url(gs_url)


def _ws(worksheet_name):
    return _open_sheet().worksheet(worksheet_name)


def _load_df(ws, limit=None, offset=0):
    kwargs = {"evaluate_formulas": True}
    if offset:
        kwargs["skip"] = offset
    if limit is not None:
        kwargs["nrows"] = limit
    return get_as_dataframe(ws, **kwargs).dropna(how="all").reset_index(drop=True)


def _resolve_columns(df, columns):
    if not columns:
        return df
    selected = []
    for c in columns:
        if c in df.columns:
            selected.append(c)
            continue
        try:
            idx = int(c)
            selected.append(df.columns[idx])
            continue
        except (ValueError, IndexError):
            pass
        parts = [p.strip() for p in c.split(",") if p.strip()]
        if all(p.isdigit() for p in parts):
            for part in parts:
                try:
                    selected.append(df.columns[int(part)])
                except IndexError:
                    cols_str = "; ".join(f"'{c}' [{i}]" for i, c in enumerate(df.columns))
                    raise click.BadParameter(
                        f"Column index '{part}' out of range.\n"
                        f"Available columns: {cols_str}"
                    )
        else:
            cols_str = "; ".join(f"'{c}' [{i}]" for i, c in enumerate(df.columns))
            raise click.BadParameter(
                f"Column '{c}' not found. Use name or 0-based index.\n"
                f"Available columns: {cols_str}\n"
                f"Tip: for multiple columns, repeat --columns flag or use comma-separated indices, e.g. --columns 0,2,5"
            )
    return df[selected]


def _filter_df(df, filters):
    if not filters:
        return df
    mask = pd.Series(True, index=df.index)
    for f in filters:
        if "=" not in f:
            raise click.BadParameter(f"Filter must be column=value, got: {f}")
        col, val = f.split("=", 1)
        if col not in df.columns:
            try:
                idx = int(col)
                col = df.columns[idx]
            except (ValueError, IndexError):
                cols_str = ", ".join(f"'{c}' ({i})" for i, c in enumerate(df.columns))
                raise click.BadParameter(
                    f"Column '{col}' not found. Use name or 0-based index.\n"
                    f"Available: {cols_str}"
                )
        mask &= df[col].astype(str).str.contains(val, case=False, na=False)
    return df[mask]


def _search_df(df, search_value):
    if not search_value:
        return df
    mask = pd.Series(False, index=df.index)
    for col in df.columns:
        mask |= df[col].astype(str).str.contains(search_value, case=False, na=False)
    return df[mask]


def _output(result_df, as_csv, output_path):
    if result_df.empty:
        click.echo("No data")
        return

    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", 40)
    pd.set_option("display.width", 200)

    if as_csv:
        buf = io.StringIO()
        result_df.to_csv(buf, index=False)
        text = buf.getvalue()
    else:
        text = result_df.to_string()

    if output_path:
        with open(output_path, "w") as f:
            f.write(text)
        click.echo(f"Written to {output_path}")
    else:
        click.echo(text)


@click.group()
def sheets():
    """Read data from Google Sheets."""


@sheets.command()
def worksheets():
    """List all worksheets in the spreadsheet."""
    sh = _open_sheet()
    for ws in sh.worksheets():
        click.echo(ws.title)


@sheets.command()
@click.argument("worksheet_name")
def columns(worksheet_name: str):
    """List column names (header row) of a worksheet."""
    ws = _ws(worksheet_name)
    df = _load_df(ws, limit=1)
    for i, col in enumerate(df.columns):
        click.echo(f"  {i}: {col}")


@sheets.command()
@click.argument("worksheet_name")
@click.option("--limit", default=50, type=int, help="Max rows to show (0 = all)")
@click.option("--offset", default=0, type=int, help="Row offset")
@click.option("--columns", "-c", multiple=True, help="Column name or 0-based index (repeatable, comma-separated)")
@click.option("--filter", "-f", "filters", multiple=True, help="Filter: column=value (repeatable)")
@click.option("--search", "-s", default=None, help="Search all columns for a value")
@click.option("--csv", "as_csv", is_flag=True, help="Output as CSV")
@click.option("--output", "-o", default=None, help="Write to file instead of stdout")
@click.option("--count", "show_count", is_flag=True, help="Only show row count")
def show(
    worksheet_name: str,
    limit: int,
    offset: int,
    columns: tuple[str, ...],
    filters: tuple[str, ...],
    search: str | None,
    as_csv: bool,
    output: str | None,
    show_count: bool,
):
    """Show data from a worksheet with filtering and column selection."""
    ws = _ws(worksheet_name)
    needs_full_load = bool(search or filters)
    if needs_full_load:
        df = _load_df(ws)
        df = _filter_df(df, filters)
        df = _search_df(df, search)
        total = len(df)
        df = df.iloc[offset:]
        if limit:
            df = df.head(limit)
    else:
        df = _load_df(ws, limit=limit if limit else None, offset=offset)
        total = None

    if show_count:
        click.echo(total if total is not None else len(df))
        return

    df = _resolve_columns(df, columns)

    _output(df, as_csv=as_csv, output_path=output)


@sheets.command()
@click.argument("worksheet_name")
@click.option("--column", "-c", default=None, help="Column name or 0-based index to search in (default: all columns)")
@click.option("--value", "-v", required=True, help="Value to search for")
@click.option("--columns", "-C", "out_columns", multiple=True,
              help="Output columns: name or 0-based index (repeatable, comma-separated indices)")
@click.option("--csv", "as_csv", is_flag=True, help="Output as CSV")
@click.option("--output", "-o", default=None, help="Write to file instead of stdout")
@click.option("--count", "show_count", is_flag=True, help="Only show match count")
@click.option("--limit", default=0, type=int, help="Max rows to show (0 = all)")
def search(
    worksheet_name: str,
    column: str | None,
    value: str,
    out_columns: tuple[str, ...],
    as_csv: bool,
    output: str | None,
    show_count: bool,
    limit: int,
):
    """Search for rows matching a value in a column (or all columns)."""
    ws = _ws(worksheet_name)
    df = _load_df(ws)

    if column:
        if column not in df.columns:
            try:
                idx = int(column)
                column = df.columns[idx]
            except (ValueError, IndexError):
                cols_str = "; ".join(f"'{c}' [{i}]" for i, c in enumerate(df.columns))
                raise click.BadParameter(
                    f"Column '{column}' not found. Use name or 0-based index.\n"
                    f"Available: {cols_str}"
                )
        mask = df[column].astype(str).str.contains(value, case=False, na=False)
    else:
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask |= df[col].astype(str).str.contains(value, case=False, na=False)

    result = df[mask]
    total = len(result)
    if limit:
        result = result.head(limit)
    result = _resolve_columns(result, out_columns)

    if show_count:
        click.echo(total)
        return

    _output(result, as_csv=as_csv, output_path=output)


def _search_ws(ws, company_name):
    """Search a worksheet for a company name, return matching rows."""
    df = _load_df(ws)
    mask = pd.Series(False, index=df.index)
    for col in df.columns:
        mask |= df[col].astype(str).str.contains(company_name, case=False, na=False)
    return df[mask].copy()


def _output_combined(combined, as_csv, output_path):
    """Output a combined DataFrame."""
    if as_csv:
        buf = io.StringIO()
        combined.to_csv(buf, index=False)
        text = buf.getvalue()
    else:
        pd.set_option("display.max_columns", None)
        pd.set_option("display.max_colwidth", 40)
        pd.set_option("display.width", 200)
        text = combined.to_string()
    if output_path:
        with open(output_path, "w") as f:
            f.write(text)
        click.echo(f"Written to {output_path}")
    else:
        click.echo(text)


@sheets.command()
@click.argument("company_name")
@click.option("--columns", "-c", multiple=True, help="Column name or 0-based index (repeatable)")
@click.option("--csv", "as_csv", is_flag=True, help="Output as CSV")
@click.option("--output", "-o", default=None, help="Write to file instead of stdout")
@click.option("--count", "show_count", is_flag=True, help="Only show match count per sheet")
def find(
    company_name: str,
    columns: tuple[str, ...],
    as_csv: bool,
    output: str | None,
    show_count: bool,
):
    """Search for a company across ALL worksheets."""
    sh = _open_sheet()

    outputs = []
    for ws in sh.worksheets():
        result = _search_ws(ws, company_name)
        if result.empty:
            continue

        result["_worksheet"] = ws.title
        if columns:
            user_cols = _resolve_columns(result, columns).columns.tolist()
            cols = ["_worksheet"] + [c for c in user_cols if c != "_worksheet"]
            result = result[cols]

        if show_count:
            outputs.append(f"{ws.title}: {len(result)}")
        else:
            outputs.append(result)

    if show_count:
        for line in outputs:
            click.echo(line)
        if not outputs:
            click.echo("No matches in any worksheet")
        return

    if not outputs:
        click.echo(f"No matches for '{company_name}' in any worksheet")
        return

    _output_combined(pd.concat(outputs, ignore_index=True), as_csv, output)
