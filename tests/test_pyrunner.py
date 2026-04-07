import json
import subprocess
import sys

import pytest

from mcc import pyrunner

resolve = pyrunner.resolve
PYRUNNER = pyrunner.__file__


class TestResolve:
    def test_dot_separated(self):
        fn = resolve("tests.example.echo")
        import tests.example as ex

        assert fn is ex.echo

    def test_colon_separated(self):
        fn = resolve("tests.example:echo")
        import tests.example as ex

        assert fn is ex.echo

    def test_chained_traversal(self):
        # resolve a nested attribute: module:Class.method style
        fn = resolve("tests.example:async_add")
        import tests.example as ex

        assert fn is ex.async_add

    def test_nonexistent_module_raises(self):
        with pytest.raises((ImportError, ModuleNotFoundError)):
            resolve("nonexistent_module_xyz.fn")

    def test_nonexistent_attr_raises(self):
        with pytest.raises(AttributeError):
            resolve("tests.example:no_such_fn")

    def test_invalid_path_raises(self):
        with pytest.raises(ImportError):
            resolve("no_dot_or_colon")


class TestPyrunnerIntrospect:
    def _run(self, *fn_paths: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, PYRUNNER, "introspect", *fn_paths],
            capture_output=True,
            text=True,
        )

    def test_stdout_is_json_array(self):
        result = self._run("tests.example:add")
        assert result.returncode == 0
        items = json.loads(result.stdout)
        assert isinstance(items, list)
        assert len(items) == 1

    def test_returns_correct_schema(self):
        result = self._run("tests.example:add")
        assert result.returncode == 0
        info = json.loads(result.stdout)[0]
        assert info["name"] == "add"
        params = {p["name"]: p for p in info["params"]}
        assert params["x"]["type"] == "int"
        assert params["x"]["required"] is True
        assert params["y"]["type"] == "int"
        assert params["y"]["required"] is True

    def test_includes_docstring(self):
        result = self._run("tests.example:documented_tool")
        assert result.returncode == 0
        info = json.loads(result.stdout)[0]
        assert "docstring" in info["doc"].lower()

    def test_return_type_annotated(self):
        result = self._run("tests.example:add")
        assert result.returncode == 0
        info = json.loads(result.stdout)[0]
        assert info["return_type"] == "int"

    def test_return_type_unannotated(self):
        result = self._run("tests.example:no_return_annotation")
        assert result.returncode == 0
        info = json.loads(result.stdout)[0]
        assert info["return_type"] is None

    def test_nonexistent_module_exits_zero(self):
        # Process must exit 0 so callers can distinguish per-item errors from crash
        result = self._run("nonexistent_module_xyz:fn")
        assert result.returncode == 0

    def test_nonexistent_module_emits_error_key(self):
        result = self._run("nonexistent_module_xyz:fn")
        items = json.loads(result.stdout)
        assert len(items) == 1
        assert "error" in items[0]
        assert items[0]["fn_path"] == "nonexistent_module_xyz:fn"

    def test_multiple_fn_paths_returns_ordered_array(self):
        result = self._run("tests.example:add", "tests.example:echo")
        assert result.returncode == 0
        items = json.loads(result.stdout)
        assert len(items) == 2
        assert items[0]["fn_path"] == "tests.example:add"
        assert items[1]["fn_path"] == "tests.example:echo"


class TestPyrunnerBatchIntrospect:
    def _run(self, *fn_paths: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, PYRUNNER, "introspect", *fn_paths],
            capture_output=True,
            text=True,
        )

    def test_valid_entries_succeed_with_invalid_mixed_in(self):
        result = self._run(
            "tests.example:add",
            "nonexistent_module_xyz:fn",
            "tests.example:echo",
        )
        assert result.returncode == 0
        items = json.loads(result.stdout)
        assert len(items) == 3
        by_path = {item["fn_path"]: item for item in items}
        assert "error" not in by_path["tests.example:add"]
        assert "error" in by_path["nonexistent_module_xyz:fn"]
        assert "error" not in by_path["tests.example:echo"]

    def test_missing_module_error_is_phase1(self):
        # Missing module → ImportError/ModuleNotFoundError in phase 1
        result = self._run("nonexistent_module_xyz:fn", "tests.example:add")
        items = json.loads(result.stdout)
        by_path = {item["fn_path"]: item for item in items}
        err = by_path["nonexistent_module_xyz:fn"]["error"]
        assert "ModuleNotFoundError" in err or "ImportError" in err

    def test_missing_attribute_error_is_phase1(self):
        # Missing attribute → AttributeError in phase 1
        result = self._run("tests.example:no_such_attr", "tests.example:add")
        items = json.loads(result.stdout)
        by_path = {item["fn_path"]: item for item in items}
        err = by_path["tests.example:no_such_attr"]["error"]
        assert "AttributeError" in err

    def test_bad_signature_is_phase2_error(self):
        # bad_signature resolves (phase 1 succeeds) but inspect.signature() raises (phase 2)
        result = self._run("tests.example:bad_signature", "tests.example:add")
        assert result.returncode == 0
        items = json.loads(result.stdout)
        by_path = {item["fn_path"]: item for item in items}
        assert "error" in by_path["tests.example:bad_signature"]
        # add is unaffected — phase-2 error on bad_signature does not stop others
        assert "error" not in by_path["tests.example:add"]

    def test_phase1_failure_does_not_prevent_phase2_for_other_fns(self):
        # A phase-1 failure should not prevent inspection of successfully resolved fns
        result = self._run(
            "nonexistent_module_xyz:fn",
            "tests.example:add",
        )
        items = json.loads(result.stdout)
        by_path = {item["fn_path"]: item for item in items}
        info = by_path["tests.example:add"]
        assert "error" not in info
        assert info["name"] == "add"


class TestPyrunnerExec:
    def _run(self, fn_path: str, kwargs: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, PYRUNNER, "exec", fn_path],
            input=json.dumps(kwargs),
            capture_output=True,
            text=True,
        )

    def test_returns_json_result(self):
        result = self._run("tests.example:add", {"x": 3, "y": 4})
        assert result.returncode == 0
        assert json.loads(result.stdout) == 7

    def test_async_fn_handled(self):
        result = self._run("tests.example:async_add", {"x": 10, "y": 5})
        assert result.returncode == 0
        assert json.loads(result.stdout) == 15

    def test_unhandled_exception_nonzero_exit(self):
        result = self._run("tests.example:always_fails", {"msg": "boom"})
        assert result.returncode != 0
        assert result.stderr  # traceback on stderr

    def test_stdout_side_effects_suppressed(self):
        # Function that calls print() must not corrupt the JSON result
        result = self._run("tests.example:noisy_add", {"x": 3, "y": 4})
        assert result.returncode == 0
        assert json.loads(result.stdout) == 7


class TestNoisyModuleIntrospect:
    def _run(self, *fn_paths: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, PYRUNNER, "introspect", *fn_paths],
            capture_output=True,
            text=True,
        )

    def test_module_level_print_suppressed(self):
        # Module with a top-level print() must not corrupt introspect JSON output
        result = self._run("tests.example_noisy:add")
        assert result.returncode == 0
        items = json.loads(result.stdout)
        assert len(items) == 1
        assert items[0]["name"] == "add"
