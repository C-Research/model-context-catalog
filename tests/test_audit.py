import mcc.audit as audit_module
import pytest
from mcc.audit import AuditIndex, _record_call, _serialize_params
from mcc.auth.models import UserModel
from mcc.models import ToolCallEvent, _call_hooks


def _event(**overrides):
    defaults = dict(
        tool_key="admin.shell",
        user=UserModel(username="alice"),
        key_prefix="abc123",
        params={"command": "ls"},
        started_at=1_700_000_000.0,
        duration=0.25,
        status="success",
        error=None,
    )
    defaults.update(overrides)
    return ToolCallEvent(**defaults)


class TestAuditDisabledByDefault:
    def test_hook_not_registered_under_default_settings(self):
        # settings.yaml ships audit_index: "" for the whole test session, so
        # mcc.audit must never have registered its hook.
        assert _record_call not in _call_hooks


class TestSerializeParams:
    def test_key_equals_value_semicolon_joined(self):
        assert _serialize_params({"a": 1, "b": "x"}) == "a=1;b=x"

    def test_empty_params(self):
        assert _serialize_params({}) == ""


class TestRecordCall:
    async def test_writes_expected_fields(self, audit_idx):
        await _record_call(_event())
        docs = await audit_idx.search({"match_all": {}})
        assert len(docs) == 1
        doc = docs[0]
        assert doc["username"] == "alice"
        assert doc["key_prefix"] == "abc123"
        assert doc["tool_key"] == "admin.shell"
        assert doc["status"] == "success"
        assert doc["error"] is None
        assert doc["params"] == "command=ls"

    async def test_anonymous_call_has_no_username_or_prefix(self, audit_idx):
        await _record_call(_event(user=None, key_prefix=None))
        docs = await audit_idx.search({"match_all": {}})
        assert docs[0]["username"] is None
        assert docs[0]["key_prefix"] is None

    async def test_error_status_recorded_as_one_liner(self, audit_idx):
        await _record_call(
            _event(status="error", error="ValueError: boom")
        )
        docs = await audit_idx.search({"match_all": {}})
        assert docs[0]["status"] == "error"
        assert docs[0]["error"] == "ValueError: boom"

    async def test_params_omitted_when_audit_params_false(
        self, audit_idx, monkeypatch
    ):
        monkeypatch.setattr(audit_module.settings, "AUDIT_PARAMS", False)
        await _record_call(_event())
        docs = await audit_idx.search({"match_all": {}})
        assert "params" not in docs[0]

    async def test_hidden_and_override_params_never_appear(self, audit_idx):
        # The event itself only ever carries visible_params values (enforced
        # in ToolModel.call(), not here) — this asserts _record_call doesn't
        # add anything beyond what's on the event.
        await _record_call(_event(params={"visible_only": "yes"}))
        docs = await audit_idx.search({"match_all": {}})
        assert docs[0]["params"] == "visible_only=yes"

    async def test_write_failure_does_not_raise(self, monkeypatch):
        async def _boom(self):
            raise RuntimeError("index unreachable")

        monkeypatch.setattr(AuditIndex, "__aenter__", _boom)
        # Must not raise -- best-effort, logged only.
        await _record_call(_event())
