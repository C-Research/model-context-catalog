from unittest.mock import MagicMock, patch

import pytest

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
    users,
)


@pytest.fixture(autouse=True)
def _fresh_db():
    users.clear_cache()
    users.truncate()
    yield
    users.truncate()


class TestCreateUser:
    def test_creates_user_with_username(self):
        create_user("alice")
        user = get_user_by_username("alice")
        assert user is not None
        assert user["username"] == "alice"

    def test_creates_user_with_email(self):
        create_user("alice", email="alice@example.com")
        user = get_user_by_username("alice")
        assert user is not None
        assert user["email"] == "alice@example.com"

    def test_creates_user_without_email(self):
        create_user("alice")
        user = get_user_by_username("alice")
        assert user is not None
        assert user["email"] is None

    def test_duplicate_username_raises(self):
        create_user("alice")
        with pytest.raises(ValueError, match="already exists"):
            create_user("alice")

    def test_duplicate_email_raises(self):
        create_user("alice", email="alice@example.com")
        with pytest.raises(ValueError, match="already exists"):
            create_user("bob", email="alice@example.com")

    def test_admin_group(self):
        create_user("alice", groups=["admin"])
        user = get_user_by_username("alice")
        assert user is not None
        assert "admin" in user["groups"]

    def test_no_token_stored(self):
        create_user("alice")
        user = get_user_by_username("alice")
        assert user is not None
        assert "token_hash" not in user


class TestDeleteUser:
    def test_deletes_user(self):
        create_user("alice")
        delete_user("alice")
        assert get_user_by_username("alice") is None

    def test_not_found_raises(self):
        with pytest.raises(ValueError, match="not found"):
            delete_user("ghost")


class TestGetUserByUsername:
    def test_found(self):
        create_user("alice")
        user = get_user_by_username("alice")
        assert user is not None
        assert user["username"] == "alice"

    def test_not_found(self):
        assert get_user_by_username("ghost") is None


class TestGetUserByEmail:
    def test_found(self):
        create_user("alice", email="alice@example.com")
        user = get_user_by_email("alice@example.com")
        assert user is not None
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"

    def test_not_found(self):
        assert get_user_by_email("ghost@example.com") is None


class TestGroups:
    def test_add_group(self):
        create_user("alice")
        add_group("alice", "ops")
        user = get_user_by_username("alice")
        assert user is not None
        assert "ops" in user["groups"]

    def test_add_group_idempotent(self):
        create_user("alice")
        add_group("alice", "ops")
        add_group("alice", "ops")
        user = get_user_by_username("alice")
        assert user is not None
        assert user["groups"].count("ops") == 1

    def test_remove_group(self):
        create_user("alice")
        add_group("alice", "ops")
        remove_group("alice", "ops")
        user = get_user_by_username("alice")
        assert user is not None
        assert "ops" not in user["groups"]

    def test_remove_group_not_member(self):
        create_user("alice")
        with pytest.raises(ValueError, match="not a member"):
            remove_group("alice", "ops")


class TestTools:
    def test_add_tool(self):
        create_user("alice")
        add_tool("alice", "echo")
        user = get_user_by_username("alice")
        assert user is not None
        assert "echo" in user["tools"]

    def test_add_tool_idempotent(self):
        create_user("alice")
        add_tool("alice", "echo")
        add_tool("alice", "echo")
        user = get_user_by_username("alice")
        assert user is not None
        assert user["tools"].count("echo") == 1

    def test_remove_tool(self):
        create_user("alice")
        add_tool("alice", "echo")
        remove_tool("alice", "echo")
        user = get_user_by_username("alice")
        assert user is not None
        assert "echo" not in user["tools"]

    def test_remove_tool_not_present(self):
        create_user("alice")
        with pytest.raises(ValueError, match="does not have tool"):
            remove_tool("alice", "echo")


class TestCanAccess:
    def _tool(self, name: str = "echo", group: str | None = None) -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.group = group
        return tool

    def test_public_group_no_user(self):
        assert can_access(None, self._tool(group="public")) is True

    def test_no_user_non_public(self):
        assert can_access(None, self._tool(group="ops")) is False

    def test_admin_bypasses(self):
        user = {"username": "admin", "groups": ["admin"], "tools": []}
        assert can_access(user, self._tool(group="ops")) is True

    def test_group_membership(self):
        user = {"username": "alice", "groups": ["ops"], "tools": []}
        assert can_access(user, self._tool(group="ops")) is True
        assert can_access(user, self._tool(group="dev")) is False

    def test_explicit_tool_grant(self):
        user = {"username": "alice", "groups": [], "tools": ["ops.echo"]}
        assert can_access(user, self._tool(name="echo", group="ops")) is True

    def test_no_access(self):
        user = {"username": "alice", "groups": [], "tools": []}
        assert can_access(user, self._tool(group="ops")) is False


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_resolves_via_email(self):
        create_user("alice", email="alice@example.com")
        mock_token = MagicMock()
        mock_token.claims = {"email": "alice@example.com", "login": "alice"}
        with patch("mcc.auth.get_access_token", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user["username"] == "alice"

    @pytest.mark.asyncio
    async def test_falls_back_to_username(self):
        create_user("alice")
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "alice"}
        with patch("mcc.auth.get_access_token", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user["username"] == "alice"

    @pytest.mark.asyncio
    async def test_email_takes_precedence_over_username(self):
        create_user("alice", email="alice@example.com")
        create_user("alice-other")
        mock_token = MagicMock()
        mock_token.claims = {"email": "alice@example.com", "login": "alice-other"}
        with patch("mcc.auth.get_access_token", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user["username"] == "alice"

    @pytest.mark.asyncio
    async def test_unauthenticated(self):
        with patch("mcc.auth.get_access_token", return_value=None):
            user = await get_current_user()
        assert user is None

    @pytest.mark.asyncio
    async def test_no_matching_record(self):
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "unknown"}
        with patch("mcc.auth.get_access_token", return_value=mock_token):
            user = await get_current_user()
        assert user is None
