from pathlib import Path

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="MCC",
    environments=True,
    settings_files=[
        str(Path(__file__).parent / "settings.toml"),
        "settings.local.toml",
    ],
    load_dotenv=True,
)
