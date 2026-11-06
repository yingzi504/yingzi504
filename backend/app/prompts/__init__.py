"""CV prompt loading independent of the working directory."""
from pathlib import Path


def load_cv_extraction_prompt() -> str:
    return Path(__file__).with_name("cv_extraction.txt").read_text(encoding="utf-8").rstrip()
