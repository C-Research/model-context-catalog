import os
import tempfile

import rich_click as click
from fastembed import TextEmbedding

from mcc.cli import console
from mcc.settings import settings


@click.command("download")
def download():
    """Pre-download the embedding model to the local cache."""
    model_name = settings.EMBEDDING_MODEL
    cache_dir = os.environ.get(
        "FASTEMBED_CACHE_PATH", os.path.join(tempfile.gettempdir(), "fastembed_cache")
    )
    console.print(f"Downloading model [bold]{model_name}[/bold] → {cache_dir}")
    TextEmbedding(model_name, cache_dir=cache_dir)
    console.print("[green]Model cached successfully.[/green]")
