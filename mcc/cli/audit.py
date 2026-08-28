"""`mcc audit` command group: read back the persisted tool-call and search
audit trails (mcc/audit.py) as paginated, filterable rich tables."""

from asyncio import run as arun

import rich_click as click
from rich.table import Table

from mcc.audit import AuditIndex, SearchAuditIndex
from mcc.cli import console
from mcc.settings import settings

_SORT_DESC: list = [{"timestamp": "desc"}]


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
def audit_tool(offset, limit, user, tool_key, since):
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

    table = Table(show_header=True, header_style="bold")
    table.add_column("Timestamp")
    table.add_column("User")
    table.add_column("Tool")
    table.add_column("Status")
    table.add_column("Duration (ms)")
    if settings.AUDIT_PARAMS:
        table.add_column("Params")
    table.add_column("Error")

    for doc in docs:
        row = [
            doc.get("timestamp") or "[dim]—[/dim]",
            doc.get("username") or "[dim]—[/dim]",
            doc.get("tool_key") or "[dim]—[/dim]",
            doc.get("status") or "[dim]—[/dim]",
            f"{doc.get('duration_ms') or 0:.1f}",
        ]
        if settings.AUDIT_PARAMS:
            row.append(doc.get("params") or "[dim]—[/dim]")
        row.append(doc.get("error") or "[dim]—[/dim]")
        table.add_row(*row)

    console.print(table)


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
def audit_search(offset, limit, user, query_text, since):
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

    table = Table(show_header=True, header_style="bold")
    table.add_column("Timestamp")
    table.add_column("User")
    table.add_column("Query")
    table.add_column("Min Score")
    table.add_column("Results")

    for doc in docs:
        min_score = doc.get("min_score")
        table.add_row(
            doc.get("timestamp") or "[dim]—[/dim]",
            doc.get("username") or "[dim]—[/dim]",
            doc.get("query") or "[dim]—[/dim]",
            f"{min_score:.2f}" if min_score is not None else "[dim]—[/dim]",
            doc.get("results") or "[dim]—[/dim]",
        )

    console.print(table)
