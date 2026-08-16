import shlex
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _quote_filter(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(shlex.quote(str(v)) for v in value)
    return shlex.quote(str(value))


jinja_env = Environment(  # nosec B701 -- output is shell commands and markdown, never
    # HTML; autoescape=True would HTML-escape shell metacharacters (e.g. `&` -> `&amp;`)
    # and corrupt both the `quote` filter's shlex output and the rendered markdown.
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    trim_blocks=True,  # removes newline after block tags
    lstrip_blocks=True,  # strips leading whitespace from block tags
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)
jinja_env.filters["quote"] = _quote_filter
