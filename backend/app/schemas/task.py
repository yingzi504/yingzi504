"""
任务相关 Pydantic schemas - Pipeline 步骤 2.10

严格定义请求体、查询参数和响应体的数据结构
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator

from app.core.jd_dictionaries import validate_department_code


class PipelineSubmitRequest(BaseModel):
    """提交处理任务请求"""
    file_id: str = Field(..., description="已上传的文件ID")
    template_type: str = Field(default="vertical", description="模板类型: vertical/horizontal")
    target_language: str = Field(default="EN", description="目标语言: CN/EN")
    job_position: Optional[str] = Field(default="", description="目标岗位")
    template_language: str = Field(default="", description="模板自身语言: CN/EN")
    department: str = Field(..., min_length=1, description="归档部门（固定部门目录，必填）")

    @field_validator("department")
    @classmethod
    def validate_department(cls, value: str) -> str:
        department = validate_department_code(value)
        if not department:
            raise ValueError("Department is required")
        return department


class GenderInputRequest(BaseModel):
    gender: Literal["male", "female"]


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态: pending/processing/completed/failed")
    progress: int = Field(..., description="进度 0-100")
    required_input: Optional[dict] = None
    current_step: str = Field(default="", description="当前步骤名称")
    step_index: int = Field(default=0, description="当前步骤序号")
    steps: list = Field(default_factory=list, description="各步骤状态列表")
    message: str = Field(default="", description="状态描述消息")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="机器可读错误码")
    error_details: Optional[dict] = Field(None, description="结构化错误详情")
    step_durations: dict = Field(default_factory=dict, description="各步骤耗时(秒)")
    total_duration: Optional[float] = Field(None, description="总耗时(秒)")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    result: Optional[dict] = Field(None, description="任务完成时的结果数据(预览&下载)")


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态")
    success: bool = Field(..., description="是否成功")
    output_filename: Optional[str] = Field(None, description="输出文件名")
    download_url: Optional[str] = Field(None, description="PPTX下载URL (向后兼容)")
    pptx_download_url: Optional[str] = Field(None, description="PPTX下载URL")
    pdf_download_url: Optional[str] = Field(None, description="PDF下载URL (需安装LibreOffice)")
    pdf_available: bool = Field(False, description="PDF版本是否可用")
    resume_data: Optional[dict] = Field(None, description="处理后的简历结构化数据")
    validation: Optional[dict] = Field(None, description="PPT验证结果")
    step_durations: dict = Field(default_factory=dict, description="各步骤耗时详情")
    total_duration: Optional[float] = Field(None, description="总耗时(秒)")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="机器可读错误码")
    error_details: Optional[dict] = Field(None, description="结构化错误详情")
    message: str = Field(default="", description="响应消息")


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskStatusResponse] = Field(default_factory=list, description="任务列表")
    total: int = Field(default=0, description="总数")
