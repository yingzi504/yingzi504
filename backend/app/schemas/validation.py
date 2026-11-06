"""验证相关的 Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ValidationIssueSchema(BaseModel):
    """单个验证问题"""
    severity: str = Field(..., description="严重程度: error | warning | info")
    category: str = Field(..., description="问题类型: overlap | text_overflow | spacing | margin")
    slide_num: int = Field(..., description="幻灯片编号 (1-based)")
    description: str = Field(..., description="问题描述")
    element1: str = Field("", description="元素1")
    element2: str = Field("", description="元素2")
    coords: str = Field("", description="坐标信息")
    suggestion: str = Field("", description="修复建议")


class ValidationResultSchema(BaseModel):
    """验证结果"""
    is_valid: bool = Field(..., description="是否通过验证")
    total_slides: int = Field(..., description="总幻灯片数")
    error_count: int = Field(0, description="错误数量")
    warning_count: int = Field(0, description="警告数量")
    info_count: int = Field(0, description="信息数量")
    errors: List[ValidationIssueSchema] = Field(default_factory=list)
    warnings: List[ValidationIssueSchema] = Field(default_factory=list)
    infos: List[ValidationIssueSchema] = Field(default_factory=list)
