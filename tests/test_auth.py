from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from mcc.auth.models import UserModel
from mcc.auth import (
    add_group,
    add_tool,
    can_access,
    create_user,
    delete_user,
    get_current_user,
    get_user_by_email,
    get_user_by_username,
    remove_group,
    remove_tool,
)


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db(users_idx):
    yield


class TestCreateUser:
    async def test_creates_user_with_username(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.username == "alice"

    async def test_creates_user_with_email(self):
        await create_user("alice", email="alice@example.com")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.email == "alice@example.com"

    async def test_creates_user_without_email(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.email is None

    async def test_duplicate_username_raises(self):
        await create_user("alice")
        with pytest.raises(ValueError, match="already exists"):
            await create_user("alice")

    async def test_duplicate_email_raises(self):
        await create_user("alice", email="alice@example.com")
        with pytest.raises(ValueError, match="already exists"):
            await create_user("bob", email="alice@example.com")

    async def test_admin_group(self):
        await create_user("alice", groups=["admin"])
        user = await get_user_by_username("alice")
        assert user is not None
        assert "admin" in user.groups

    async def test_no_token_stored(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert not hasattr(user, "token_hash")


class TestDeleteUser:
    async def test_deletes_user(self):
        await create_user("alice")
        await delete_user("alice")
        assert await get_user_by_username("alice") is None

    async def test_not_found_raises(self):
        with pytest.raises(ValueError, match="not found"):
            await delete_user("ghost")


class TestGetUserByUsername:
    async def test_found(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.username == "alice"

    async def test_not_found(self):
        assert await get_user_by_username("ghost") is None


class TestGetUserByEmail:
    async def test_found(self):
        await create_user("alice", email="alice@example.com")
        user = await get_user_by_email("alice@example.com")
        assert user is not None
        assert user.username == "alice"
        assert user.email == "alice@example.com"

    async def test_not_found(self):
        assert await get_user_by_email("ghost@example.com") is None


class TestGroups:
    async def test_add_group(self):
        await create_user("alice")
        await add_group("alice", "ops")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "ops" in user.groups

    async def test_add_group_idempotent(self):
        await create_user("alice")
        await add_group("alice", "ops")
        await add_group("alice", "ops")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.groups.count("ops") == 1

    async def test_remove_group(self):
        await create_user("alice")
        await add_group("alice", "ops")
        await remove_group("alice", "ops")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "ops" not in user.groups

    async def test_remove_group_not_member(self):
        await create_user("alice")
        with pytest.raises(ValueError, match="not a member"):
            await remove_group("alice", "ops")


class TestTools:
    async def test_add_tool(self):
        await create_user("alice")
        await add_tool("alice", "echo")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "echo" in user.tools

    async def test_add_tool_idempotent(self):
        await create_user("alice")
        await add_tool("alice", "echo")
        await add_tool("alice", "echo")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.tools.count("echo") == 1

    async def test_remove_tool(self):
        await create_user("alice")
        await add_tool("alice", "echo")
        await remove_tool("alice", "echo")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "echo" not in user.tools

    async def test_remove_tool_not_present(self):
        await create_user("alice")
        with pytest.raises(ValueError, match="does not have tool"):
            await remove_tool("alice", "echo")


class TestCanAccess:
    def _tool(self, name: str = "echo", groups: list[str] | None = None) -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.groups = groups or []
        tool.key = ".".join(sorted(tool.groups) + [name])
        return tool

    def test_empty_groups_no_user(self):
        assert can_access(None, self._tool(groups=[])) is True

    def test_no_user_with_groups(self):
        assert can_access(None, self._tool(groups=["ops"])) is False

    def test_admin_bypasses(self):
        user = UserModel(username="admin", groups=["admin"])
        assert can_access(user, self._tool(groups=["ops"])) is True

    def test_group_membership(self):
        user = UserModel(username="alice", groups=["ops"])
        assert can_access(user, self._tool(groups=["ops"])) is True
        assert can_access(user, self._tool(groups=["dev"])) is False

    def test_explicit_tool_grant(self):
        user = UserModel(username="alice", tools=["ops.echo"])
        assert can_access(user, self._tool(name="echo", groups=["ops"])) is True

    def test_no_access(self):
        user = UserModel(username="alice")
        assert can_access(user, self._tool(groups=["ops"])) is False


class TestGetCurrentUser:
    async def test_resolves_via_email(self):
        await create_user("alice", email="alice@example.com")
        mock_token = MagicMock()
        mock_token.claims = {"email": "alice@example.com", "login": "alice"}
        with patch("mcc.auth.backend.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.username == "alice"

    async def test_falls_back_to_username(self):
        await create_user("alice")
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "alice"}
        with patch("mcc.auth.backend.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.username == "alice"

    async def test_email_takes_precedence_over_username(self):
        await create_user("alice", email="alice@example.com")
        await create_user("alice-other")
        mock_token = MagicMock()
        mock_token.claims = {"email": "alice@example.com", "login": "alice-other"}
        with patch("mcc.auth.backend.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.username == "alice"

    async def test_unauthenticated(self):
        with patch("mcc.auth.backend.get_user_context", return_value=None):
            user = await get_current_user()
        assert user is None

    async def test_no_matching_record(self):
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "unknown"}
        with patch("mcc.auth.backend.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is None
