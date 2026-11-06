import io
import logging

from app.core import logging_config


def test_application_logger_writes_warning_to_terminal_stream():
    app_logger = logging.getLogger("app")
    original_handlers = list(app_logger.handlers)
    original_level = app_logger.level
    original_propagate = app_logger.propagate
    original_stderr = logging_config.sys.stderr
    stream = io.StringIO()

    try:
        app_logger.handlers.clear()
        logging_config.sys.stderr = stream
        logging_config.configure_application_logging(debug=True)
        logging.getLogger("app.services.translator_service").warning(
            "translation step warning"
        )

        output = stream.getvalue()
        assert "WARNING app.services.translator_service" in output
        assert "translation step warning" in output
    finally:
        app_logger.handlers.clear()
        app_logger.handlers.extend(original_handlers)
        app_logger.setLevel(original_level)
        app_logger.propagate = original_propagate
        logging_config.sys.stderr = original_stderr
