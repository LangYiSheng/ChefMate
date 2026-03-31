from __future__ import annotations

import logging


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
