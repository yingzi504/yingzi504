"""Canonical degree wording shared by extraction and final CV output."""
import re
from typing import Optional
from app.core.cv_rules import CV_RULES


def normalize_degree(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    text = str(value).strip()
    # Keep subject and completion status, e.g. 工学硕士、博士（在读）.
    text = re.sub(r"博士\s*研究生", "博士", text)
    text = re.sub(r"硕士\s*研究生", "硕士", text)
    text = re.sub(r"(?:大学)?本科(?:学历)?", "学士", text)
    text = re.sub(r"学士\s*[/／、（(]?\s*学士\s*[）)]?", "学士", text)
    text = re.sub(r"研究生(?:学历)?", lambda _: CV_RULES.ambiguous_degree_label, text)
    return text
