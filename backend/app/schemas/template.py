"""模板 Pydantic Schemas — 步骤4.5"""
from typing import Optional
from pydantic import BaseModel, Field


class TemplateResponse(BaseModel):
    """模板信息响应（与前端 Template 接口对齐）"""
    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    category: str = Field(..., description="分类: vertical / horizontal")
    version: str = Field(default="1.0", description="版本号")
    updateTime: str = Field(default="", description="更新时间")
    filePath: str = Field(default="", description="文件路径")
    status: str = Field(default="active", description="状态: active / inactive")


class TemplateUpdateRequest(BaseModel):
    """更新模板信息请求"""
    name: Optional[str] = Field(None, description="模板名称")
    category: Optional[str] = Field(None, description="分类")
    version: Optional[str] = Field(None, description="版本号")
    status: Optional[str] = Field(None, description="状态: active / inactive")
