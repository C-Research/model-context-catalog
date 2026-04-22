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

CONTRIB = Path(__file__).parents[1]

from mcc.auth import create_user  # noqa: E402
from mcc.auth.models import UserModel  # noqa: E402
from mcc.db import UsersIndex  # noqa: E402
from mcc.loader import loader  # noqa: E402
from mcc.middleware import current_user_var  # noqa: E402


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
