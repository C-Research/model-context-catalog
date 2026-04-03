def echo(message: str) -> str:
    return [message]


def documented_tool(message: str) -> str:
    """A tool loaded from its docstring."""
    return [message]


async def async_echo(message: str) -> str:
    return [message]
