"""Opt-in, persisted audit trail of catalog tool calls.

Disabled unless `settings.audit_index` is a non-empty string — in that case
it both enables auditing and names the index. Registers a hook (via
`mcc.models.on_tool_call`) that fires only for calls whose underlying
callable actually ran (success or error); calls vetoed by rate limiting,
denied by authorization, cancelled during elicitation, or served from
`execute()`'s result cache never reach `ToolModel.call()` and are therefore
never audited.
"""

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from mcc.db import IndexBase
from mcc.models import ToolCallEvent, on_tool_call
from mcc.settings import logger, settings


class AuditIndex(IndexBase):
    """Append-only: one document per audited tool call, id=uuid4()."""

    index = settings.AUDIT_INDEX
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


def _serialize_params(params: dict) -> str:
    """"key=var;key=var" text -- for human/grep reading, not structured querying."""
    return ";".join(f"{key}={value}" for key, value in params.items())


async def _record_call(event: ToolCallEvent) -> None:
    doc: dict = {
        "timestamp": datetime.fromtimestamp(event.started_at, tz=UTC).isoformat(),
        "username": event.user.username if event.user else None,
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


if settings.AUDIT_INDEX:
    on_tool_call(_record_call)
