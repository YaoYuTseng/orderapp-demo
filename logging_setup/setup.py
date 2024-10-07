import json
import logging
import logging.config
from pathlib import Path


def setup_logging() -> logging.Logger:
    with open(Path("logging_setup", "config.json"), "r") as f:
        config = json.load(f)
        logging.config.dictConfig(config)
    logger = logging.getLogger("orderapp")
    return logger


LOGGER = setup_logging()
