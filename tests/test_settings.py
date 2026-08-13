import importlib
import logging


def test_debug_setting_forces_mcc_logger_to_debug(monkeypatch):
    from mcc import settings as settings_mod

    original_level = settings_mod.logger.level
    monkeypatch.setenv("MCC_DEBUG", "true")
    try:
        importlib.reload(settings_mod)
        assert settings_mod.logger.level == logging.DEBUG
    finally:
        monkeypatch.delenv("MCC_DEBUG", raising=False)
        importlib.reload(settings_mod)
        settings_mod.logger.setLevel(original_level)


def test_debug_defaults_to_false(monkeypatch):
    from mcc import settings as settings_mod

    monkeypatch.delenv("MCC_DEBUG", raising=False)
    assert settings_mod.settings.get("DEBUG", False) is False
