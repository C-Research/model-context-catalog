import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.update(
    {
        "MCC_AUTH": "dev-admin",
        "MCC_USER_INDEX": "mcc-users-test",
        "MCC_TOOL_INDEX": "mcc-tools-test",
    }
)

CONTRIB = Path(__file__).parents[1]


def state_backed_ctx(session="s1"):
    """A mock FastMCP Context whose get_state/set_state are awaitable and backed by
    an in-memory, session-scoped store (mirroring FastMCP's `{session_id}:{key}`
    prefixing). execute() awaits get_state/set_state, so a bare MagicMock is not
    enough — its attributes must be AsyncMocks."""
    store: dict = {}

    async def _get(key):
        return store.get(f"{session}:{key}")

    async def _set(key, value):
        store[f"{session}:{key}"] = value

    ctx = MagicMock()
    ctx.get_state = AsyncMock(side_effect=_get)
    ctx.set_state = AsyncMock(side_effect=_set)
    return ctx


# Shared across the contrib test suite. Safe as a single instance because these
# tools are stateless (none declare a `context` param, so nothing writes back);
# the backing store stays empty. If a contrib tool ever persists session state,
# switch to a per-test fixture to avoid cross-test bleed.
CTX = state_backed_ctx()

from mcc.auth import create_user
from mcc.context import UserModel
from mcc.db import UsersIndex
from mcc.loader import loader
from mcc.middleware import current_user_var


@pytest.fixture
async def users_idx():
    async with UsersIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def load_contrib(users_idx):
    loader.clear()
    await create_user("test", groups=["admin"])
    current_user_var.set(UserModel(username="test", groups=["admin"]))
    yield lambda fn: loader.load(CONTRIB / fn)
    loader.clear()
    current_user_var.set(None)
