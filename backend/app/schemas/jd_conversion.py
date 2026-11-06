from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.jd_dictionaries import validate_department_code


JDCategory = Literal["technical", "non_technical"]
JDOutputLanguage = Literal["CN", "EN", "CNEN"]
JDTargetPositionSource = Literal["manual", "filename", "content"]
JDRecognitionSource = Literal["filename", "content"]


class BilingualItems(BaseModel):
    cn: list[str] = Field(default_factory=list)
    en: list[str] = Field(default_factory=list)


class JDRequirements(BaseModel):
    education: BilingualItems = Field(default_factory=BilingualItems)
    experience: BilingualItems = Field(default_factory=BilingualItems)
    required_skills: BilingualItems = Field(default_factory=BilingualItems)
    language: BilingualItems = Field(default_factory=BilingualItems)
    preferred: BilingualItems = Field(default_factory=BilingualItems)
    soft_skills: BilingualItems = Field(default_factory=BilingualItems)


class JDContent(BaseModel):
    title_cn: str = ""
    title_en: str = ""
    location_cn: str = ""
    location_en: str = ""
    department: str = ""
    category: JDCategory = "technical"
    responsibilities_cn: list[str] = Field(default_factory=list)
    responsibilities_en: list[str] = Field(default_factory=list)
    requirements: JDRequirements = Field(default_factory=JDRequirements)

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str) -> str:
        return validate_department_code(value)


class JDConversionRequest(BaseModel):
    file_id: Optional[str] = None
    original_filename: str = ""
    source_text: Optional[str] = None
    department: str = ""
    category: JDCategory = "technical"
    target_position: str = ""
    target_position_source: JDTargetPositionSource = "content"
    # Retained for compatibility with clients created before target-position detection.
    target_direction: str = ""
    output_language: JDOutputLanguage = "CN"

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str) -> str:
        return validate_department_code(value)

    @model_validator(mode="after")
    def validate_source(self):
        has_file = bool((self.file_id or "").strip())
        has_text = bool((self.source_text or "").strip())
        if has_file and has_text:
            raise ValueError("Provide at most one JD source: file_id or source_text")

        manual_target = bool((self.target_position or self.target_direction).strip())
        if self.target_position_source == "manual" and not manual_target:
            raise ValueError("A target position is required for manual position input")
        if self.target_position_source == "filename" and not has_file:
            raise ValueError("Filename position detection requires an uploaded file")
        if self.target_position_source == "content" and not (has_file or has_text):
            raise ValueError("Content position detection requires a file or source text")
        if not (has_file or has_text or manual_target):
            raise ValueError("Provide a JD source or a manual target position")
        return self


class JDPositionRecognitionRequest(BaseModel):
    file_id: Optional[str] = None
    original_filename: str = ""
    source_text: Optional[str] = None
    target_position_source: JDRecognitionSource
    output_language: JDOutputLanguage = "CN"

    @model_validator(mode="after")
    def validate_source(self):
        has_file = bool((self.file_id or "").strip())
        has_text = bool((self.source_text or "").strip())
        if has_file and has_text:
            raise ValueError("Provide at most one JD source: file_id or source_text")
        if self.target_position_source == "filename":
            if not has_file:
                raise ValueError("Filename position detection requires an uploaded file")
            if not self.original_filename.strip():
                raise ValueError("Original filename is required for filename position detection")
        if self.target_position_source == "content" and not (has_file or has_text):
            raise ValueError("Content position detection requires a file or source text")
        return self


class JDRegenerateRequest(BaseModel):
    content: JDContent


class JDLocationRequest(BaseModel):
    location: str = Field(min_length=1, max_length=200)

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        location = str(value or "").strip()
        if not location:
            raise ValueError("Work location is required")
        return location
