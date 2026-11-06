"""Pydantic schemas for the JD library."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.jd_dictionaries import validate_department_code


def _normalize_language(value: str) -> str:
    aliases = {
        "zh": "CN",
        "cn": "CN",
        "en": "EN",
        "cnen": "CNEN",
        "cn+en": "CNEN",
    }
    cleaned = str(value or "CN").strip()
    return aliases.get(cleaned.lower(), cleaned.upper())


class JDCreateRequest(BaseModel):
    title: str = ""
    department: str = ""
    category: str
    language: str = "CN"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    active: bool = True
    is_hot: bool = False

    @model_validator(mode="before")
    @classmethod
    def accept_frontend_aliases(cls, value: Any):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        data["title"] = data.get("title") or data.get("position") or ""
        data["description"] = data.get("description") or data.get("content") or ""
        if "isHot" in data and "is_hot" not in data:
            data["is_hot"] = data["isHot"]
        return data

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = str(value or "").strip()
        if not title:
            raise ValueError("JD title is required")
        return title

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str) -> str:
        return validate_department_code(value)

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return _normalize_language(value)


class JDUpdateRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    active: Optional[bool] = None
    is_hot: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def accept_frontend_aliases(cls, value: Any):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "position" in data and "title" not in data:
            data["title"] = data["position"]
        if "content" in data and "description" not in data:
            data["description"] = data["content"]
        if "isHot" in data and "is_hot" not in data:
            data["is_hot"] = data["isHot"]
        return data

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: Optional[str]) -> Optional[str]:
        return validate_department_code(value or "") if value is not None else None

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_language(value) if value is not None else None


class JDResponse(BaseModel):
    id: str
    title: str
    position: str = ""
    department: str = ""
    category: str
    language: str = "CN"
    isHot: bool = False
    description: str = ""
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    active: bool = True
    structuredData: Optional[dict] = None
    createTime: str = ""
    usageCount: int = 0
    lastUsed: str = ""
    updatedAt: str = ""
