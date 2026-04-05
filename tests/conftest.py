import os
from pathlib import Path

import pytest


os.environ.update(
    {
        "MCC_AUTH": "dangerous",
        "MCC_ELASTICSEARCH__USER_INDEX": "mcc-users-test",
        "MCC_ELASTICSEARCH__TOOL_INDEX": "mcc-tools-test",
        "MCC_CONTRIB": "true",
    }
)
CONTRIB = Path(__file__).parents[1] / "mcc" / "contrib"
FIXTURES = Path(__file__).parent / "fixtures"


from mcc.db import ToolIndex, UsersIndex  # noqa: E402
from mcc.loader import loader, load_file as load  # noqa: E402
from mcc.auth import create_user  # noqa: E402
from mcc.auth.models import UserModel  # noqa: E402
from mcc.middleware import current_user_var  # noqa: E402


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
async def load_contrib(users_idx):
    loader.clear()
    await create_user("test", groups=["admin"])
    current_user_var.set(UserModel(username="test", groups=["admin"]))
    yield lambda fn: loader.load(CONTRIB / fn)
    loader.clear()
    current_user_var.set(None)


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
