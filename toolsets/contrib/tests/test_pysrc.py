import pytest

from mcc.app import execute

from .conftest import CTX as _CTX


@pytest.fixture(autouse=True)
async def _load(load_contrib):
    load_contrib("pysrc.yaml")


class TestGetDocstring:
    async def test_returns_docstring(self):
        result = await execute(
            _CTX, "admin.dev.get_docstring", {"fn_path": "mcc.pyrunner:resolve"}
        )
        assert "Resolve a dotpath" in result

    async def test_no_docstring_returns_empty_string(self):
        result = await execute(
            _CTX, "admin.dev.get_docstring", {"fn_path": "mcc.loader:load_file"}
        )
        assert result == ""


class TestGetSource:
    async def test_returns_source(self):
        result = await execute(
            _CTX, "admin.dev.get_source", {"fn_path": "mcc.loader:_resolve_python"}
        )
        assert "def _resolve_python" in result
        assert "shutil.which" in result


class TestGetSignature:
    async def test_required_and_optional_params(self):
        result = await execute(
            _CTX, "admin.dev.get_signature", {"fn_path": "mcc.loader:load_file"}
        )
        assert isinstance(result, dict)
        assert result["params"] == [
            {"name": "path", "type": "str", "required": True, "default": None}
        ]

    async def test_variadic_params_excluded(self):
        result = await execute(
            _CTX, "admin.dev.get_signature", {"fn_path": "mcc.pyrunner:introspect"}
        )
        assert isinstance(result, dict)
        names = [p["name"] for p in result["params"]]
        assert "fn_paths" not in names


class TestListMembers:
    async def test_excludes_reexported_imports(self):
        result = await execute(
            _CTX, "admin.dev.list_members", {"module_path": "mcc.db"}
        )
        assert isinstance(result, list)
        names = [m["name"] for m in result]
        assert "AsyncElasticsearch" not in names
        assert "ToolIndex" in names

    async def test_kind_filters_to_class(self):
        result = await execute(
            _CTX,
            "admin.dev.list_members",
            {"module_path": "mcc.db", "kind": "class"},
        )
        assert isinstance(result, list)
        assert result
        assert all(m["kind"] == "class" for m in result)

    async def test_kind_filters_to_function(self):
        result = await execute(
            _CTX,
            "admin.dev.list_members",
            {"module_path": "mcc.pyrunner", "kind": "function"},
        )
        assert isinstance(result, list)
        names = [m["name"] for m in result]
        assert "resolve" in names
        assert all(m["kind"] == "function" for m in result)


class TestGetClassHierarchy:
    async def test_bases_and_subclasses(self):
        result = await execute(
            _CTX, "admin.dev.get_class_hierarchy", {"fn_path": "mcc.loader:Loader"}
        )
        assert isinstance(result, dict)
        assert "builtins.dict" in result["bases"]
        assert result["subclasses"] == []


class TestGetFileLocation:
    async def test_returns_file_and_line_range(self):
        result = await execute(
            _CTX, "admin.dev.get_file_location", {"fn_path": "mcc.loader:load_file"}
        )
        assert isinstance(result, dict)
        assert result["file"].endswith("mcc/loader.py")
        assert result["lineno"] < result["endlineno"]


class TestResolveErrors:
    async def test_malformed_path_raises_import_error(self):
        # fn tools run in a subprocess; errors come back as (code, stdout, stderr)
        result = await execute(
            _CTX, "admin.dev.get_docstring", {"fn_path": "not a valid path"}
        )
        code, _, stderr = result
        assert code != 0
        assert "Invalid fn path" in stderr
