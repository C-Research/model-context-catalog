"""`mcc audit` command group: read back the persisted tool-call and search
audit trails (mcc/audit.py) as paginated, filterable rich tables, or export
them as CSV/JSON to stdout or a file."""

import csv
import json
from asyncio import run as arun
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Any

import rich_click as click
from rich.console import Console
from rich.table import Table

from mcc.audit import AuditIndex, SearchAuditIndex
from mcc.cli import console
from mcc.settings import settings

_SORT_DESC: list = [{"timestamp": "desc"}]

# (header, doc key, optional value formatter for table/csv display)
_Column = tuple[str, str, Callable[[Any], Any] | None]


def _output_options(fn):
    fn = click.option(
        "-O",
        "--output",
        "output_path",
        default=None,
        type=click.Path(dir_okay=False, writable=True),
        help="Write output to this file instead of stdout.",
    )(fn)
    fn = click.option(
        "-f",
        "--format",
        "fmt",
        type=click.Choice(["table", "csv", "json"]),
        default="table",
        show_default=True,
        help="Output format.",
    )(fn)
    return fn


def _term_clauses(since: str | None = None, **terms) -> list[dict]:
    """Builds `term`/`range` query clauses from keyword filters (None values
    skipped) plus an optional `since` range on `timestamp`."""
    clauses = [
        {"term": {field: value}} for field, value in terms.items() if value is not None
    ]
    if since is not None:
        clauses.append({"range": {"timestamp": {"gte": since}}})
    return clauses


def _bool_query(clauses: list[dict]) -> dict:
    return {"bool": {"must": clauses}} if clauses else {"match_all": {}}


async def _fetch(idx_cls, query: dict, offset: int, limit: int) -> list[dict]:
    """Runs `query` against `idx_cls`'s backing index, newest-first, paginated.

    Calls create() first (a no-op if the index already exists) so a
    never-written-to index reads back as empty rather than raising a
    backend-specific not-found error."""
    async with idx_cls() as idx:
        await idx.create()
        return await idx.search(query, limit=limit, offset=offset, sort=_SORT_DESC)


def _write(text: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(text)
        console.print(f"[dim]Wrote output to {output_path}[/dim]")
    else:
        print(text, end="")


def _render(docs: list[dict], columns: list[_Column], fmt: str, output_path: str | None) -> None:
    """Renders `docs` as a rich table (to stdout only) or CSV/JSON (to stdout
    or `output_path`), using `columns` to select and format fields."""
    if fmt == "json":
        payload = [{key: doc.get(key) for _, key, _ in columns} for doc in docs]
        _write(json.dumps(payload, indent=2, default=str), output_path)
        return

    if fmt == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([header for header, _, _ in columns])
        for doc in docs:
            writer.writerow([_value(doc, key, formatter) for _, key, formatter in columns])
        _write(buf.getvalue(), output_path)
        return

    table = Table(show_header=True, header_style="bold")
    for header, _, _ in columns:
        table.add_column(header)
    for doc in docs:
        table.add_row(
            *[_display(doc, key, formatter) for _, key, formatter in columns]
        )
    if output_path:
        with open(output_path, "w") as f:
            Console(file=f, markup=True).print(table)
        console.print(f"[dim]Wrote output to {output_path}[/dim]")
    else:
        console.print(table)


def _value(doc: dict, key: str, formatter: Callable[[Any], Any] | None) -> Any:
    value = doc.get(key)
    return formatter(value) if formatter else value


def _display(doc: dict, key: str, formatter: Callable[[Any], Any] | None) -> str:
    value = _value(doc, key, formatter)
    return str(value) if value not in (None, "") else "[dim]—[/dim]"


@click.group()
def audit():
    """View persisted audit logs."""


@audit.command("tool")
@click.option(
    "-o", "--offset", default=0, show_default=True, help="Number of records to skip."
)
@click.option(
    "-l", "--limit", default=20, show_default=True, help="Max records to show."
)
@click.option("--user", default=None, help="Filter to a single username.")
@click.option("--tool-key", default=None, help="Filter to a single tool key.")
@click.option(
    "--since", default=None, help="Only records at or after this ISO timestamp/date."
)
@_output_options
def audit_tool(offset, limit, user, tool_key, since, fmt, output_path):
    """List persisted tool-call audit records, newest first."""
    if not settings.AUDIT_TOOL_INDEX:
        console.print(
            "[dim]Tool-call auditing is not configured (audit_tool_index is unset).[/dim]"
        )
        return

    query = _bool_query(_term_clauses(since=since, username=user, tool_key=tool_key))
    docs = arun(_fetch(AuditIndex, query, offset, limit))
    if not docs:
        console.print("[dim]No tool-call audit records found.[/dim]")
        return

    columns: list[_Column] = [
        ("Timestamp", "timestamp", None),
        ("User", "username", None),
        ("Tool", "tool_key", None),
        ("Status", "status", None),
        ("Duration (ms)", "duration_ms", lambda v: f"{v or 0:.1f}"),
    ]
    if settings.AUDIT_PARAMS:
        columns.append(("Params", "params", None))
    columns.append(("Error", "error", None))

    _render(docs, columns, fmt, output_path)


@audit.command("search")
@click.option(
    "-o", "--offset", default=0, show_default=True, help="Number of records to skip."
)
@click.option(
    "-l", "--limit", default=20, show_default=True, help="Max records to show."
)
@click.option("--user", default=None, help="Filter to a single username.")
@click.option(
    "--query", "query_text", default=None, help="Filter to records whose query text matches."
)
@click.option(
    "--since", default=None, help="Only records at or after this ISO timestamp/date."
)
@_output_options
def audit_search(offset, limit, user, query_text, since, fmt, output_path):
    """List persisted search audit records, newest first."""
    if not settings.AUDIT_SEARCH_INDEX:
        console.print(
            "[dim]Search auditing is not configured (audit_search_index is unset).[/dim]"
        )
        return

    clauses = _term_clauses(since=since, username=user)
    if query_text:
        clauses.append({"match": {"query": query_text}})
    docs = arun(_fetch(SearchAuditIndex, _bool_query(clauses), offset, limit))
    if not docs:
        console.print("[dim]No search audit records found.[/dim]")
        return

    columns: list[_Column] = [
        ("Timestamp", "timestamp", None),
        ("User", "username", None),
        ("Query", "query", None),
        ("Min Score", "min_score", lambda v: f"{v:.2f}" if v is not None else None),
        ("Results", "results", None),
    ]

    _render(docs, columns, fmt, output_path)
