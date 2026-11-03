"""Logging: console + processing.log inside the output directory."""

import logging
import os


def setup_logging(output_dir: str, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("microstock")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)
    try:
        os.makedirs(output_dir, exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join(output_dir, "processing.log"), encoding="utf-8"
        )
    except OSError:
        file_handler = None
    else:
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    return logger
