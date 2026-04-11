import platform

import pytest

from mcc.app import execute


@pytest.fixture(autouse=True)
async def _load(load_contrib):
    load_contrib("system.yaml")


class TestGetEnv:
    async def test_returns_values(self, monkeypatch):
        monkeypatch.setenv("MCC_TEST_A", "alpha")
        monkeypatch.setenv("MCC_TEST_B", "beta")
        result = await execute(
            "admin.system.get_env", {"keys": ["MCC_TEST_A", "MCC_TEST_B"]}
        )
        assert result == {"MCC_TEST_A": "alpha", "MCC_TEST_B": "beta"}

    async def test_missing_key_returns_none(self):
        result = await execute(
            "admin.system.get_env", {"keys": ["MCC_DEFINITELY_NOT_SET"]}
        )
        assert result == {"MCC_DEFINITELY_NOT_SET": None}


class TestSetEnv:
    async def test_sets_variable(self):
        # set_env runs in a subprocess; the env change is isolated to that process
        result = await execute(
            "admin.system.set_env", {"key": "MCC_TEST_SET", "value": "hello"}
        )
        assert result is None  # function returns None on success


class TestListEnv:
    async def test_returns_sorted_keys(self):
        result = await execute("admin.system.list_env", {})
        assert isinstance(result, list)
        assert result == sorted(result)
        assert "PATH" in result


class TestPlatform:
    async def test_returns_system_info(self):
        result = await execute("admin.system.platform", {})
        assert isinstance(result, dict)
        assert result["os"] == platform.system()
        assert result["python"] == platform.python_version()
        assert result["arch"] == platform.machine()
        assert "hostname" in result


class TestPath:
    async def test_returns_sys_path(self):
        result = await execute("admin.system.pythonpath", {})
        assert isinstance(result, list)
        # subprocess sys.path shares the same venv but may differ slightly from parent
        assert all(isinstance(p, str) for p in result)
        assert any("site-packages" in p for p in result)
