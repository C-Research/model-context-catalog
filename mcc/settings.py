import logging.config
from os import getenv
from pathlib import Path

from dynaconf import Dynaconf

settings_files = [
    str(Path(__file__).parent / "settings.yaml"),
    str(Path.cwd() / "settings.local.yaml"),
]
if getenv("MCC_SETTINGS_FILES"):
    settings_files.extend(getenv("MCC_SETTINGS_FILES").split(";"))

settings = Dynaconf(
    envvar_prefix="MCC",
    environments=True,
    settings_files=settings_files,
    load_dotenv=True,
)

logging.config.dictConfig(settings.LOGGING.to_dict())
logger = logging.getLogger("mcc")
