"""Application logging configured for terminal-first diagnostics."""

import logging
import sys


_HANDLER_NAME = "ai-resume-terminal"


def configure_application_logging(debug: bool = False) -> None:
    """Send all ``app.*`` logs to the process terminal without duplication."""
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    handler = next(
        (item for item in app_logger.handlers if item.get_name() == _HANDLER_NAME),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.set_name(_HANDLER_NAME)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        ))
        app_logger.addHandler(handler)

    handler.setLevel(logging.DEBUG if debug else logging.INFO)
    app_logger.propagate = False
