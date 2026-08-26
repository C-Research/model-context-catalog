import importlib
import sys
import types

import pytest

from toolsets.contrib import scraping
from toolsets.contrib.scraping import scrape


class _Result:
    def __init__(self, values):
        self._values = values

    def getall(self):
        return list(self._values)


class _Page:
    def __init__(self, css_map=None, xpath_map=None):
        self._css_map = css_map or {}
        self._xpath_map = xpath_map or {}

    def css(self, selector):
        return _Result(self._css_map.get(selector, []))

    def xpath(self, selector):
        return _Result(self._xpath_map.get(selector, []))


def _install_fake_scrapling(monkeypatch, get=None, js_fetch=None, stealth_fetch=None):
    """Injects a fake `scrapling` module so scrape()'s lazy import picks it up,
    without depending on the real package or the network."""

    async def default_get(url, **kwargs):
        return _Page()

    class AsyncFetcher:
        @staticmethod
        async def get(url, **kwargs):
            return await (get or default_get)(url, **kwargs)

    class DynamicFetcher:
        @staticmethod
        async def async_fetch(url, **kwargs):
            return await (js_fetch or default_get)(url, **kwargs)

    class StealthyFetcher:
        @staticmethod
        async def async_fetch(url, **kwargs):
            return await (stealth_fetch or default_get)(url, **kwargs)

    fake_module = types.ModuleType("scrapling")
    fake_module.AsyncFetcher = AsyncFetcher
    fake_module.DynamicFetcher = DynamicFetcher
    fake_module.StealthyFetcher = StealthyFetcher
    monkeypatch.setitem(sys.modules, "scrapling", fake_module)


class TestFieldExtraction:
    async def test_css_only(self, monkeypatch):
        async def get(url, **kwargs):
            return _Page(css_map={"h1::text": ["Example Domain"]})

        _install_fake_scrapling(monkeypatch, get=get)
        result = await scrape(["https://example.com"], css={"title": "h1::text"})
        assert result == {"https://example.com": {"title": ["Example Domain"]}}

    async def test_xpath_only(self, monkeypatch):
        async def get(url, **kwargs):
            return _Page(xpath_map={"//h1/text()": ["Example Domain"]})

        _install_fake_scrapling(monkeypatch, get=get)
        result = await scrape(["https://example.com"], xpath={"title": "//h1/text()"})
        assert result == {"https://example.com": {"title": ["Example Domain"]}}

    async def test_css_and_xpath_merge(self, monkeypatch):
        async def get(url, **kwargs):
            return _Page(
                css_map={"h1::text": ["Example Domain"]},
                xpath_map={"//a/@href": ["https://iana.org/domains/example"]},
            )

        _install_fake_scrapling(monkeypatch, get=get)
        result = await scrape(
            ["https://example.com"],
            css={"title": "h1::text"},
            xpath={"links": "//a/@href"},
        )
        assert result == {
            "https://example.com": {
                "title": ["Example Domain"],
                "links": ["https://iana.org/domains/example"],
            }
        }


class TestValidation:
    async def test_requires_css_or_xpath(self, monkeypatch):
        _install_fake_scrapling(monkeypatch)
        with pytest.raises(ValueError):
            await scrape(["https://example.com"])

    async def test_invalid_mode(self, monkeypatch):
        _install_fake_scrapling(monkeypatch)
        with pytest.raises(ValueError):
            await scrape(
                ["https://example.com"], css={"title": "h1::text"}, mode="bogus"
            )


class TestFailureIsolation:
    async def test_one_bad_url_does_not_break_others(self, monkeypatch):
        async def get(url, **kwargs):
            if url == "https://bad.example.com":
                raise TimeoutError("boom")
            return _Page(css_map={"h1::text": ["ok"]})

        _install_fake_scrapling(monkeypatch, get=get)
        result = await scrape(
            ["https://good.example.com", "https://bad.example.com"],
            css={"title": "h1::text"},
        )
        assert result["https://good.example.com"] == {"title": ["ok"]}
        assert result["https://bad.example.com"] == "TimeoutError: boom"

    async def test_all_succeed(self, monkeypatch):
        async def get(url, **kwargs):
            return _Page(css_map={"h1::text": ["ok"]})

        _install_fake_scrapling(monkeypatch, get=get)
        result = await scrape(
            ["https://a.example.com", "https://b.example.com"],
            css={"title": "h1::text"},
        )
        assert result == {
            "https://a.example.com": {"title": ["ok"]},
            "https://b.example.com": {"title": ["ok"]},
        }


class TestModeDispatch:
    async def test_js_uses_dynamic_fetcher(self, monkeypatch):
        calls = []

        async def js_fetch(url, **kwargs):
            calls.append(url)
            return _Page(css_map={"h1::text": ["rendered"]})

        _install_fake_scrapling(monkeypatch, js_fetch=js_fetch)
        result = await scrape(
            ["https://example.com"], css={"title": "h1::text"}, mode="js"
        )
        assert calls == ["https://example.com"]
        assert result == {"https://example.com": {"title": ["rendered"]}}

    async def test_stealth_uses_stealthy_fetcher(self, monkeypatch):
        calls = []

        async def stealth_fetch(url, **kwargs):
            calls.append(url)
            return _Page(css_map={"h1::text": ["stealthed"]})

        _install_fake_scrapling(monkeypatch, stealth_fetch=stealth_fetch)
        result = await scrape(
            ["https://example.com"], css={"title": "h1::text"}, mode="stealth"
        )
        assert calls == ["https://example.com"]
        assert result == {"https://example.com": {"title": ["stealthed"]}}


class TestOptionalDependency:
    def test_module_imports_without_scrapling(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "scrapling", None)
        importlib.reload(scraping)

    async def test_missing_dependency_raises_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "scrapling", None)
        with pytest.raises(ImportError, match=r"model-context-catalog\[scraping\]"):
            await scrape(["https://example.com"], css={"title": "h1::text"})


class TestGroupSplit:
    """`fn` tools execute in an isolated subprocess (mcc.exec.make_py_callable), so
    scrapling can't be mocked through execute() here — verify the override at the
    schema level instead: the public entry must hide `mode` and force it to
    "static", while the admin entry leaves it fully caller-controlled."""

    def _load(self):
        from mcc.loader import load_file

        return {
            t.key: t
            for t in load_file(
                scraping.__file__.replace("scraping.py", "scraping.yaml")
            )
        }

    def test_public_forces_static_mode(self):
        tools = self._load()
        public = tools["public.scraping.scrape-static"]
        assert "mode" not in [p.name for p in public.visible_params]
        hidden = {p.name: p.override for p in public.hidden_params}
        assert hidden["mode"] == "static"

    def test_admin_leaves_mode_uncontrolled(self):
        tools = self._load()
        admin = tools["admin.scraping.scrape"]
        assert "mode" in [p.name for p in admin.visible_params]
        assert admin.hidden_params == []
