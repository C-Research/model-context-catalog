import os
from pathlib import Path

import pytest

os.environ.update(
    {
        "MCC_AUTH": "dev-admin",
        "MCC_ELASTICSEARCH__USER_INDEX": "mcc-users-test",
        "MCC_ELASTICSEARCH__TOOL_INDEX": "mcc-tools-test",
    }
)
FIXTURES = Path(__file__).parent / "fixtures"


from mcc.cache import cache  # noqa: E402
from mcc.db import ToolIndex, UsersIndex  # noqa: E402
from mcc.loader import load_file as load  # noqa: E402
from mcc.loader import loader  # noqa: E402


@pytest.fixture(autouse=True)
async def clear_cache():
    await cache.clear()
    yield
    await cache.clear()


@pytest.fixture
async def tool_idx():
    async with ToolIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def users_idx():
    async with UsersIndex() as idx:
        await idx.drop()
        await idx.create()
        yield idx
        await idx.drop()


@pytest.fixture
async def load_fixture():
    def _inner(*fns):
        loader.clear()
        for fn in fns:
            loader.load(FIXTURES / fn)

    return _inner


@pytest.fixture
async def load_file():
    return lambda fn: load(FIXTURES / fn)
