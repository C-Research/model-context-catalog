def echo(message: str) -> list[str]:
    return [message]


def documented_tool(message: str) -> list[str]:
    """A tool loaded from its docstring."""
    return [message]


async def async_echo(message: str) -> list[str]:
    return [message]
