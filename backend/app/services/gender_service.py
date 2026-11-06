"""Read explicit gender declarations without guessing from names or photos."""
import re
import unicodedata
from typing import Optional


def detect_source_gender(text: str) -> Optional[str]:
    text = unicodedata.normalize("NFKC", text or "")
    pattern = r"(?:性\s*别|(?<![a-z])gender|(?<![a-z])sex)\s*[:：=]?\s*(female|male|女性|男性|女|男|[mf])(?=$|[\s,，;；|/。])"
    values = re.findall(pattern, text, re.I)
    header = "\n".join(text.splitlines()[:12])[:800]
    values.extend(re.findall(r"(?:^|[|｜,，;；\n])\s*(female|male|女|男)\s*(?=$|[|｜,，;；\n])", header, re.I))
    genders = {"female" if v.lower() in {"female", "f", "女", "女性"} else "male" for v in values}
    return genders.pop() if len(genders) == 1 else None
