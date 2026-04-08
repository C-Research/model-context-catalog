import shlex
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _quote_filter(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(shlex.quote(str(v)) for v in value)
    return shlex.quote(str(value))


jinja_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    trim_blocks=True,  # removes newline after block tags
    lstrip_blocks=True,  # strips leading whitespace from block tags
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)
jinja_env.filters["quote"] = _quote_filter
