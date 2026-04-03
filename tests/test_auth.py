import os
import tempfile

import pytest

from mcc.auth import (
    add_group,
    add_tool,
    can_access,
    create_user,
    db,
    delete_user,
    get_user_by_name,
    get_user_by_token,
    hash_token,
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


class TestTokenUtils:
    def test_hash_token_prefix(self):
        h = hash_token("abc")
        assert h.startswith("sha256:")

    def test_hash_token_deterministic(self):
        assert hash_token("abc") == hash_token("abc")

    def test_hash_token_differs(self):
        assert hash_token("abc") != hash_token("def")


class TestCreateUser:
    def test_creates_user(self):
        token = create_user("alice")
        assert isinstance(token, str)
        assert len(token) == 64

    def test_duplicate_raises(self):
        create_user("alice")
        with pytest.raises(ValueError, match="already exists"):
            create_user("alice")

    def test_admin_group(self):
        create_user("admin", groups=["admin"])
        user = get_user_by_name("admin")
        assert "admin" in user["groups"]


class TestDeleteUser:
    def test_deletes_user(self):
        create_user("alice")
        delete_user("alice")
        assert get_user_by_name("alice") is None

    def test_not_found_raises(self):
        with pytest.raises(ValueError, match="not found"):
            delete_user("ghost")


class TestGetUser:
    def test_by_token(self):
        token = create_user("alice")
        user = get_user_by_token(token)
        assert user["username"] == "alice"
        assert "token_hash" not in user

    def test_by_token_invalid(self):
        assert get_user_by_token("bad") is None

    def test_by_name(self):
        create_user("alice")
        user = get_user_by_name("alice")
        assert user["username"] == "alice"
        assert "token_hash" not in user

    def test_by_name_not_found(self):
        assert get_user_by_name("ghost") is None


class TestGroups:
    def test_add_group(self):
        create_user("alice")
        add_group("alice", "ops")
        user = get_user_by_name("alice")
        assert "ops" in user["groups"]

    def test_add_group_idempotent(self):
        create_user("alice")
        add_group("alice", "ops")
        add_group("alice", "ops")
        user = get_user_by_name("alice")
        assert user["groups"].count("ops") == 1

    def test_remove_group(self):
        create_user("alice")
        add_group("alice", "ops")
        remove_group("alice", "ops")
        user = get_user_by_name("alice")
        assert "ops" not in user["groups"]

    def test_remove_group_not_member(self):
        create_user("alice")
        with pytest.raises(ValueError, match="not a member"):
            remove_group("alice", "ops")


class TestTools:
    def test_add_tool(self):
        create_user("alice")
        add_tool("alice", "echo")
        user = get_user_by_name("alice")
        assert "echo" in user["tools"]

    def test_add_tool_idempotent(self):
        create_user("alice")
        add_tool("alice", "echo")
        add_tool("alice", "echo")
        user = get_user_by_name("alice")
        assert user["tools"].count("echo") == 1

    def test_remove_tool(self):
        create_user("alice")
        add_tool("alice", "echo")
        remove_tool("alice", "echo")
        user = get_user_by_name("alice")
        assert "echo" not in user["tools"]

    def test_remove_tool_not_present(self):
        create_user("alice")
        with pytest.raises(ValueError, match="does not have tool"):
            remove_tool("alice", "echo")


class TestCanAccess:
    def test_public_group_no_user(self):
        assert can_access(None, "echo", "public") is True

    def test_no_user_non_public(self):
        assert can_access(None, "echo", "ops") is False

    def test_admin_bypasses(self):
        user = {"username": "admin", "groups": ["admin"], "tools": []}
        assert can_access(user, "echo", "ops") is True

    def test_group_membership(self):
        user = {"username": "alice", "groups": ["ops"], "tools": []}
        assert can_access(user, "echo", "ops") is True
        assert can_access(user, "echo", "dev") is False

    def test_explicit_tool_grant(self):
        user = {"username": "alice", "groups": [], "tools": ["ops.echo"]}
        assert can_access(user, "ops.echo", "ops") is True

    def test_no_access(self):
        user = {"username": "alice", "groups": [], "tools": []}
        assert can_access(user, "echo", "ops") is False
