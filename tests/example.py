def add(x: int, y: int) -> int:
    return x + y


async def async_add(x: int, y: int) -> int:
    return x + y


def always_fails(msg: str) -> str:
    raise RuntimeError(msg)


def echo(message: str) -> list[str]:
    return [message]


def documented_tool(message: str) -> list[str]:
    """A tool loaded from its docstring."""
    return [message]


async def async_echo(message: str) -> list[str]:
    return [message]


def echo_with_flag(message: str, flag: bool = False) -> dict:
    return {"message": message, "flag": flag}


def get_env_var(name: str) -> str | None:
    import os

    return os.environ.get(name)


def needs_context(x: int, context: dict) -> dict:
    """fn tool declaring a `context` param: pyrunner injects the context dict."""
    return {"x": x, "context": context}


def no_context(x: int) -> int:
    """fn tool with no `context` param: nothing is injected."""
    return x


def stash_cursor(n: int, context: dict) -> int:
    """Writes to its context (write-back), returns a plain result."""
    context["cursor"] = n
    return n


def clear_context(context: dict) -> str:
    """Empties its context: full-replace write-back clears non-identity vars."""
    for key in list(context):
        del context[key]
    return "cleared"


def spoof_identity(context: dict) -> str:
    """Tries to overwrite and delete reserved identity keys via write-back."""
    context["user"] = "admin"
    context.pop("groups", None)
    return "tried"


def bad_key(context: dict) -> str:
    """Writes an invalid (non-slug) key: whole write-back must be rejected."""
    context["bad key"] = 1
    return "ok"


def echo_list(items: list, context: dict) -> list:
    """Returns a list result while also writing back, to test envelope unwrapping."""
    context["seen"] = True
    return items


def no_return_annotation(x: int):
    return x


class _BadSignature:
    """A callable whose __signature__ property raises, triggering a phase-2 error."""

    @property
    def __signature__(self):
        raise TypeError("deliberate signature error for testing")

    def __call__(self):
        pass


bad_signature = _BadSignature()


def noisy_add(x: int, y: int) -> int:
    print("side effect output")
    return x + y
