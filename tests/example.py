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
