import logging.config
from pathlib import Path

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="MCC",
    environments=True,
    settings_files=[
        str(Path(__file__).parent / "settings.yaml"),
        str(Path.cwd() / "settings.local.yaml"),
    ],
    load_dotenv=True,
)

logging.config.dictConfig(settings.LOGGING.to_dict())
logger = logging.getLogger("mcc")
