"""历史记录 Pydantic Schemas — 步骤4.5"""
from typing import Optional, List
from pydantic import BaseModel, Field


class HistoryItemResponse(BaseModel):
    """历史记录响应（与前端 HistoryItem 接口对齐）"""
    id: str = Field(..., description="记录ID")
    timestamp: str = Field(default="", description="处理时间")
    originalFile: str = Field(default="", description="原始文件名")
    fileSize: str = Field(default="", description="文件大小")
    jobPosition: str = Field(default="", description="目标岗位")
    language: str = Field(default="CN", description="语言")
    template: str = Field(default="", description="模板类型")
    jdMatchScore: Optional[int] = Field(None, description="JD匹配度")
    status: str = Field(default="completed", description="状态: completed / failed")
    processingTime: str = Field(default="", description="处理耗时")
    outputFile: str = Field(default="", description="输出文件名")


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""
    success: bool = Field(default=True)
    data: List[HistoryItemResponse] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    pageSize: int = Field(default=10)
    message: str = Field(default="")
    timestamp: str = Field(default="")


class StatisticsResponse(BaseModel):
    """统计信息响应（与前端 Statistics 接口对齐）"""
    total: int = Field(default=0, description="总处理数")
    successRate: float = Field(default=0.0, description="成功率")
    monthly: int = Field(default=0, description="本月处理数")
