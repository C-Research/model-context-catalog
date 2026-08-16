"""Storage/search backend dispatch.

Picks the Elasticsearch- (`mcc.db.es`) or OpenSearch- (`mcc.db.os`) backed
implementation of `UsersIndex`, `KeysIndex`, `ToolIndex`, and `session_store`
based on `settings.SEARCH_BACKEND`, and re-exports it under one name each.
`mcc.db.os` (and `opensearch-py`) is only imported when that backend is
selected, so an Elasticsearch-only install never needs it present.
"""

from mcc.settings import settings

if settings.SEARCH_BACKEND == "opensearch":
    from mcc.db import os as _backend
else:
    from mcc.db import es as _backend

UsersIndex = _backend.UsersIndex
KeysIndex = _backend.KeysIndex
ToolIndex = _backend.ToolIndex
session_store = _backend.session_store
