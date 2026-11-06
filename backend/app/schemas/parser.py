"""
文件解析相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ParseRequest(BaseModel):
    """解析请求"""
    file_id: str = Field(..., description="文件ID")


class ParseResponse(BaseModel):
    """解析响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional["ParseResult"] = Field(None, description="解析结果")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")


class ParseResult(BaseModel):
    """解析结果"""
    file_id: str = Field(..., description="文件ID")
    original_file: str = Field(..., description="原始文件名")
    text_content: str = Field(..., description="提取的文本内容")
    file_type: str = Field(..., description="文件类型（pdf/docx/image）")
    parse_method: str = Field(..., description="解析方法（unstructured/ocr）")
    parse_duration: float = Field(..., description="解析耗时（秒）")
    page_count: Optional[int] = Field(None, description="页数（PDF）")


# 更新前向引用
ParseResponse.update_forward_refs()
