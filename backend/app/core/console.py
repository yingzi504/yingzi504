"""Console stream configuration shared by backend entry points."""

import sys
from typing import Iterable, Optional, TextIO


def configure_console_output(streams: Optional[Iterable[TextIO]] = None) -> None:
    """Keep diagnostic output from crashing on non-UTF-8 Windows consoles."""
    output_streams = streams if streams is not None else (sys.stdout, sys.stderr)
    for stream in output_streams:
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            # Test runners and redirected streams may not support reconfigure().
            pass
