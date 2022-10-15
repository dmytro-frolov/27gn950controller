import logging
import pathlib
import platform

log = logging.getLogger(__name__)


def return_type(value):
    if value.lower() in ["true", "false"]:
        return value.lower() == "true"

    if value.isnumeric():
        return int(value)

    return value


class Config:
    def __init__(self):
        self.config = pathlib.Path()
        match platform.system():
            case "Darwin":
                self.config = (
                    pathlib.Path.home() / "Library/Application "
                    "Support/BiasController/"
                )
            case "Windows":
                self.config = pathlib.Path("%AppData%/BiasController/")

        self.config /= "config.ini"

        self.config_exist = False
        self.read_config()

    def read_config(self):
        if not self.config.exists():
            log.error("config.ini is missing")
            return

        with self.config.open("r") as f:
            for line in f.readlines():
                if not line.strip():
                    continue

                key, value = line.strip().split("=")
                setattr(self, key, return_type(value))
        self.config_exist = True
