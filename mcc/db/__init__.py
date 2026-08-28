"""Storage/search backend dispatch.

Picks the Elasticsearch- (`mcc.db.es`) or OpenSearch- (`mcc.db.os`) backed
implementation of `UsersIndex`, `KeysIndex`, `ToolIndex`, and `session_store`
based on `settings.SEARCH_BACKEND`, and re-exports it under one name each.
`mcc.db.os` (and `opensearch-py`) is only imported when that backend is
selected, so an Elasticsearch-only install never needs it present.
"""

from typing import TYPE_CHECKING

from mcc.settings import settings

# The runtime dispatch below picks the backend module by a settings value
# pyright can't evaluate, so a plain `X = _backend.X` alias isn't usable as a
# base class downstream (e.g. AuditIndex(IndexBase) in mcc/audit.py) — pyright
# sees an ambiguous value, not a concrete `type[...]`. Giving it one fixed,
# concrete import path under TYPE_CHECKING (arbitrarily the ES module; the ES
# and OS classes have identical shapes) fixes that without changing runtime
# behavior, since TYPE_CHECKING is always False at runtime.
if TYPE_CHECKING:
    from mcc.db.es import IndexBase, KeysIndex, ToolIndex, UsersIndex, session_store
else:
    if settings.SEARCH_BACKEND == "opensearch":
        from mcc.db import os as _backend
    else:
        from mcc.db import es as _backend

    UsersIndex = _backend.UsersIndex
    KeysIndex = _backend.KeysIndex
    ToolIndex = _backend.ToolIndex
    IndexBase = _backend.IndexBase
    session_store = _backend.session_store
