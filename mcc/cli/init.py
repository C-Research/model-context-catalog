from asyncio import run as arun

import rich_click as click

from mcc.audit import AuditIndex, SearchAuditIndex
from mcc.cli import console
from mcc.db import KeysIndex, UsersIndex
from mcc.settings import settings


def _configured_indices() -> list[type]:
    """Index classes `mcc init` creates: users and keys always, plus each audit
    index whose setting is non-empty (empty means auditing is off)."""
    indices: list[type] = [UsersIndex, KeysIndex]
    if settings.AUDIT_TOOL_INDEX:
        indices.append(AuditIndex)
    if settings.AUDIT_SEARCH_INDEX:
        indices.append(SearchAuditIndex)
    return indices


async def _create(idx_cls) -> None:
    async with idx_cls() as idx:
        await idx.create()


@click.command("init")
def init():
    """Create the Elasticsearch/OpenSearch indices mcc needs, if missing.

    Creates the users and keys indices, plus the audit indices when
    `audit_tool_index` / `audit_search_index` are set. Safe to re-run: indices
    that already exist are left untouched.

    The tool index is not created here — `mcc tool reindex` builds it.
    """
    for idx_cls in _configured_indices():
        arun(_create(idx_cls))
        console.print(f"[green]Ready:[/green] {idx_cls.index}")
