import hashlib
from unittest.mock import MagicMock

import pytest

from mcc.app import execute

_CTX = MagicMock()


@pytest.fixture(autouse=True)
async def _load(load_contrib):
    load_contrib("text.yaml")


class TestBase64:
    async def test_encode(self):
        assert (
            await execute(_CTX, "public.text.base64_encode", {"text": "hello"}) == "aGVsbG8="
        )

    async def test_decode(self):
        assert (
            await execute(_CTX, "public.text.base64_decode", {"text": "aGVsbG8="}) == "hello"
        )

    async def test_roundtrip(self):
        encoded = await execute(_CTX, "public.text.base64_encode", {"text": "round trip 🚀"})
        decoded = await execute(_CTX, "public.text.base64_decode", {"text": encoded})
        assert decoded == "round trip 🚀"


class TestHash:
    async def test_sha256_default(self):
        expected = hashlib.sha256(b"hello").hexdigest()
        assert await execute(_CTX, "public.text.hash", {"text": "hello"}) == expected

    async def test_md5(self):
        expected = hashlib.md5(b"hello").hexdigest()
        assert (
            await execute(_CTX, "public.text.hash", {"text": "hello", "algo": "md5"})
            == expected
        )


class TestRegex:
    async def test_search_finds_matches(self):
        result = await execute(_CTX,
            "public.text.regex_search", {"pattern": r"\d+", "string": "abc 123 def 456"}
        )
        assert result == ["123", "456"]

    async def test_search_no_match(self):
        result = await execute(_CTX,
            "public.text.regex_search", {"pattern": r"\d+", "string": "no digits"}
        )
        assert result == []

    async def test_replace(self):
        result = await execute(_CTX,
            "public.text.regex_replace",
            {"pattern": r"\d+", "repl": "X", "string": "a1b2c3"},
        )
        assert result == "aXbXcX"


class TestDiff:
    async def test_identical(self):
        result = await execute(_CTX, "public.text.diff", {"a": "same", "b": "same"})
        assert result == ""

    async def test_shows_changes(self):
        result = await execute(_CTX,
            "public.text.diff",
            {"a": "line one\nline two\n", "b": "line one\nline THREE\n"},
        )
        assert "-line two" in result
        assert "+line THREE" in result
