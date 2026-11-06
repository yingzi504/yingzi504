"""JD Pydantic Schemas — 步骤4.5"""
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.jd_library import JDCreateRequest, JDResponse, JDUpdateRequest


class _LegacyJDCreateRequest(BaseModel):
    """创建 JD 请求"""
    title: str = Field(..., description="JD 标题")
    category: str = Field(..., description="分类")
    language: str = Field(default="CN", description="语言: CN / EN")
    description: str = Field(default="", description="JD 详细描述")
    is_hot: bool = Field(default=False, description="是否热门标记")


class _LegacyJDUpdateRequest(BaseModel):
    """更新 JD 请求"""
    title: Optional[str] = Field(None, description="标题")
    category: Optional[str] = Field(None, description="分类")
    language: Optional[str] = Field(None, description="语言")
    description: Optional[str] = Field(None, description="描述")
    is_hot: Optional[bool] = Field(None, description="热门标记")


class _LegacyJDResponse(BaseModel):
    """JD 响应（与前端 JD 接口对齐）"""
    id: str = Field(..., description="JD ID")
    title: str = Field(..., description="标题")
    category: str = Field(..., description="分类")
    language: str = Field(default="CN", description="语言")
    isHot: bool = Field(default=False, description="热门标记")
    description: str = Field(default="", description="描述")
    createTime: str = Field(default="", description="创建时间")
    usageCount: int = Field(default=0, description="使用次数")
    lastUsed: str = Field(default="", description="最后使用时间")
