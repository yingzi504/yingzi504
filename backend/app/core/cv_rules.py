"""Executable CV policy defaults. Human-readable index: docs/CV生成规范.md.

Loaded when the backend starts; restart after changing these values.
Keep environment/deployment settings in core.config instead.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CVRules:
    extraction_max_input_chars: int = 12000  # CV-IN-02
    translation_max_attempts: int = 3  # CV-TR-05
    body_font_size_pt: int = 12  # CV-LAYOUT-02
    module_spacing_cm: float = 0.5  # CV-LAYOUT-03
    ambiguous_degree_label: str = "学位未注明"  # CV-EDU-02

    def __post_init__(self):
        for field in ("extraction_max_input_chars", "translation_max_attempts", "body_font_size_pt"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field} must be a positive integer")
        if not 0 <= self.module_spacing_cm <= 5:
            raise ValueError("module_spacing_cm must be between 0 and 5")
        if not self.ambiguous_degree_label.strip():
            raise ValueError("ambiguous_degree_label must not be empty")


CV_RULES = CVRules()


def cv_download_filename(filename: str) -> str:
    """Hide only the generated CV storage suffix; preserve dates and extensions."""
    import re
    return re.sub(
        r"^(IAV_.+_Resume_(?:CN|EN)_\d{8})_[0-9a-f]{12}(\.(?:pptx|pdf))$",
        r"\1\2", filename, flags=re.IGNORECASE,
    )
