"""Opt-in, persisted audit trails: catalog tool calls, and catalog searches.

Tool-call auditing is disabled unless `settings.audit_tool_index` is a
non-empty string — in that case it both enables auditing and names the
index. Registers a hook (via `mcc.models.on_tool_call`) that fires only for
calls whose underlying callable actually ran (success or error); calls
vetoed by rate limiting, denied by authorization, cancelled during
elicitation, or served from `execute()`'s result cache never reach
`ToolModel.call()` and are therefore never audited.

Search auditing is disabled unless `settings.audit_search_index` is a
non-empty string. Unlike tool-call auditing, there is no hook: `search()`
(`mcc/app.py`) is the only call site (no REST /search route exists), so
`_record_search` is called directly rather than through a registry with a
single consumer.
"""

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from mcc.db import IndexBase
from mcc.models import ToolCallEvent, on_tool_call
from mcc.settings import logger, settings


class AuditIndex(IndexBase):
    """Append-only: one document per audited tool call, id=uuid4()."""

    index = settings.AUDIT_TOOL_INDEX
    mapping: ClassVar[dict] = {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "username": {"type": "keyword"},
                "key_prefix": {"type": "keyword"},
                "tool_key": {"type": "keyword"},
                "params": {"type": "text"},
                "status": {"type": "keyword"},
                "error": {"type": "text"},
                "duration_ms": {"type": "float"},
            }
        }
    }


class SearchAuditIndex(IndexBase):
    """Append-only: one document per audited search() call, id=uuid4()."""

    index = settings.AUDIT_SEARCH_INDEX
    mapping: ClassVar[dict] = {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "username": {"type": "keyword"},
                "query": {"type": "text"},
                "min_score": {"type": "float"},
                "results": {"type": "text"},
            }
        }
    }


def _serialize_params(params: dict) -> str:
    """"key=var;key=var" text -- for human/grep reading, not structured querying."""
    return ";".join(f"{key}={value}" for key, value in params.items())


def _serialize_results(pairs: list[tuple[str, float]]) -> str:
    """"key=score;key=score" text, in result order -- same convention as
    _serialize_params, for human/grep reading, not structured querying."""
    return ";".join(f"{key}={score:.2f}" for key, score in pairs)


async def _record_call(event: ToolCallEvent) -> None:
    doc: dict = {
        "timestamp": datetime.fromtimestamp(event.started_at, tz=UTC).isoformat(),
        "username": None if event.user.is_anonymous else event.user.username,
        "key_prefix": event.key_prefix,
        "tool_key": event.tool_key,
        "status": event.status,
        "error": event.error,
        "duration_ms": event.duration * 1000,
    }
    if settings.AUDIT_PARAMS:
        doc["params"] = _serialize_params(event.params)
    try:
        async with AuditIndex() as idx:
            await idx.create()
            await idx.put(str(uuid.uuid4()), doc)
    except Exception:  # noqa: BLE001 -- audit write failures must never fail the triggering tool call
        logger.exception("failed to write audit record for %s", event.tool_key)


async def _record_search(
    username: str | None,
    query: str,
    min_score: float | None,
    pairs: list[tuple[str, float]],
) -> None:
    doc: dict = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "username": username,
        "query": query,
        "min_score": min_score,
        "results": _serialize_results(pairs),
    }
    try:
        async with SearchAuditIndex() as idx:
            await idx.create()
            await idx.put(str(uuid.uuid4()), doc)
    except Exception:  # noqa: BLE001 -- audit write failures must never fail the triggering search call
        logger.exception("failed to write search audit record for query %r", query)


if settings.AUDIT_TOOL_INDEX:
    on_tool_call(_record_call)
