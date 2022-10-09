import logging
import pathlib

log = logging.getLogger(__name__)


def return_type(value):
    if value.lower() in ["true", "false"]:
        return value.lower() == "true"

    if value.isnumeric():
        return int(value)

    return value


# todo: pyinstall doesn't see config
def read_config():
    config = pathlib.Path("~/.lgbiascontroller/config.ini")
    if not config.exists():
        log.error("config.ini is missing")

    result = {}
    with config.open("r") as f:
        for line in f.readlines():
            if not line.strip():
                continue

            key, value = line.strip().split("=")
            result[key] = return_type(value)

    return result
