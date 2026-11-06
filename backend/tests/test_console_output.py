import io

from app.core.console import configure_console_output


def test_console_output_accepts_emoji_from_gbk_stream():
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="gbk", newline="")

    configure_console_output((stream,))
    stream.write("\n📋 PPT template filling")
    stream.flush()

    assert stream.encoding.lower() == "utf-8"
    assert buffer.getvalue().decode("utf-8") == "\n📋 PPT template filling"
    stream.detach()
