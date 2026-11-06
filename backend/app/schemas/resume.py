from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union
from datetime import datetime
from app.schemas.education import normalize_degree


class WorkItem(BaseModel):
    """工作经历条目"""
    company: Optional[str] = Field(None, description="公司名称")
    period: Optional[str] = Field(None, description="时间段")
    role: Optional[str] = Field(None, description="职位/角色")
    tasks: Optional[str] = Field(None, description="工作内容/任务")


class ProjectItem(BaseModel):
    """项目经历条目"""
    company: Optional[str] = Field(None, description="公司名称")
    period: Optional[str] = Field(None, description="时间段")
    name: Optional[str] = Field(None, description="项目名称")
    role: Optional[str] = Field(None, description="角色")
    tasks: Optional[str] = Field(None, description="项目内容/任务")


class EducationItem(BaseModel):
    """教育经历条目"""
    period: Optional[str] = Field(None, description="时间段")
    school: Optional[str] = Field(None, description="学校")
    degree: Optional[str] = Field(None, description="学位")
    major: Optional[str] = Field(None, description="专业")


    @field_validator("degree", mode="before")
    @classmethod
    def canonical_degree(cls, value):
        return normalize_degree(value)


class ResumeData(BaseModel):
    """简历结构化数据（匹配PPT模板字段）"""
    name: Optional[str] = Field(None, description="姓名")
    anonymized_name: Optional[str] = Field(None, description="脱敏姓名")
    anonymized_name_cn: Optional[str] = Field(None, description="中文脱敏姓名")
    phone: Optional[str] = Field(None, description="电话")
    email: Optional[str] = Field(None, description="邮箱")
    location: Optional[str] = Field(None, description="所在地")
    age: Optional[int] = Field(None, description="年龄")
    birth_date: Optional[str] = Field(None, description="出生日期")
    gender: Optional[str] = Field(None, description="性别: male/female，CV流程使用原文明确标注或用户确认")
    
    position: Optional[str] = Field(None, description="职位")
    job_position: Optional[str] = Field(None, description="目标岗位")
    job_position_en: Optional[str] = Field(None, description="目标岗位英文名称")
    technical_area: Optional[str] = Field(None, description="技术领域")
    total_exp: Optional[str] = Field(None, description="总工作经验")
    
    education: List[EducationItem] = Field(default_factory=list, description="教育经历")
    work: List[WorkItem] = Field(default_factory=list, description="工作经历")
    project: List[ProjectItem] = Field(default_factory=list, description="项目经历")
    
    tech_skills: Optional[Union[str, List[str]]] = Field(None, description="技术技能")
    lang_skills: Optional[Union[str, List[str]]] = Field(None, description="语言技能")
    lang_skills_level: Optional[str] = Field(None, description="语言水平")
    training_exp: Optional[str] = Field(None, description="培训经历")
    
    summary: Optional[str] = Field(None, description="个人简介")
    language: str = Field(default="CN", description="语言 CN/EN")
    is_anonymized: bool = Field(default=False, description="是否已脱敏")

    @field_validator("tech_skills", "lang_skills", mode="before")
    @classmethod
    def normalize_skills_to_string(cls, v):
        """将数组类型的技能转为逗号分隔字符串，兼容 LLM 返回的两种格式"""
        if isinstance(v, list):
            return ", ".join(str(item) for item in v if item)
        return v


class ProcessRequest(BaseModel):
    """简历处理请求"""
    file_id: str = Field(..., description="文件ID")
    template_id: str = Field(..., description="模板ID")
    target_language: Optional[str] = Field("CN", description="目标语言")
    job_position: Optional[str] = Field(None, description="目标岗位")
    jd_text: Optional[str] = Field(None, description="JD文本")


class ExtractionRequest(BaseModel):
    """信息抽取请求"""
    raw_text: str = Field(..., description="原始文本内容")


class ExtractionResponse(BaseModel):
    """信息抽取响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[ResumeData] = Field(None, description="结构化简历数据")
    message: str = Field(..., description="响应消息")


class ProcessResponse(BaseModel):
    """简历处理响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态")
    resume_data: Optional[ResumeData] = Field(None, description="结构化简历数据")


class TranslationRequest(BaseModel):
    """翻译请求"""
    resume_data: ResumeData = Field(..., description="简历数据")
    target_language: Optional[str] = Field(None, description="目标语言 CN/EN")
    template_language: Optional[str] = Field(None, description="模板语言 CN/EN，如果提供则优先使用作为目标语言")


class TranslationResponse(BaseModel):
    """翻译响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[ResumeData] = Field(None, description="翻译后的简历数据")
    message: str = Field(..., description="响应消息")


class AnonymizationRequest(BaseModel):
    """脱敏请求"""
    resume_data: ResumeData = Field(..., description="简历数据")


class AnonymizationResponse(BaseModel):
    """脱敏响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[ResumeData] = Field(None, description="脱敏后的简历数据")
    message: str = Field(..., description="响应消息")


class TransformRequest(BaseModel):
    """翻译+脱敏联合处理请求（Pipeline步骤3）"""
    resume_data: ResumeData = Field(..., description="简历数据")
    target_language: Optional[str] = Field(None, description="目标语言 CN/EN，不填则不翻译")
    template_language: Optional[str] = Field(None, description="模板语言 CN/EN，如果提供则优先使用作为目标语言")
    perform_anonymization: bool = Field(default=True, description="是否执行脱敏")


class TransformResponse(BaseModel):
    """翻译+脱敏联合处理响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[ResumeData] = Field(None, description="处理后的简历数据")
    message: str = Field(..., description="响应消息")


class SummarizationRequest(BaseModel):
    """摘要优化请求"""
    resume_data: ResumeData = Field(..., description="简历数据")


class SummarizationResponse(BaseModel):
    """摘要优化响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[ResumeData] = Field(None, description="优化后的简历数据")
    message: str = Field(..., description="响应消息")


class FillerRequest(BaseModel):
    """PPT填充请求"""
    resume_data: ResumeData = Field(..., description="简历数据")
    template_type: str = Field(default="vertical", description="模板类型 (vertical/horizontal)")
    generate_pdf: bool = Field(default=True, description="是否同时生成PDF版本")


class FillerResponse(BaseModel):
    """PPT填充响应"""
    success: bool = Field(..., description="是否成功")
    output_path: Optional[str] = Field(None, description="PPTX输出文件路径")
    filename: Optional[str] = Field(None, description="输出文件名")
    pptx_download_url: Optional[str] = Field(None, description="PPTX下载URL")
    pdf_download_url: Optional[str] = Field(None, description="PDF下载URL (需安装LibreOffice)")
    file_size: Optional[int] = Field(None, description="PPTX文件大小(字节)")
    pdf_file_size: Optional[int] = Field(None, description="PDF文件大小(字节)")
    pdf_available: bool = Field(False, description="PDF是否可用")
    message: str = Field(..., description="响应消息")
    validation: Optional[dict] = Field(None, description="PPT验证结果 (包含重叠/溢出等检查)")
    needs_fix: bool = Field(False, description="是否需要修复验证发现的问题")


class OutputFileInfo(BaseModel):
    """输出文件信息"""
    filename: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小(字节)")
    size_display: str = Field(..., description="文件大小(可读)")
    created_at: Optional[str] = Field(None, description="创建时间")
    modified_at: Optional[str] = Field(None, description="修改时间")
    pptx_download_url: str = Field(..., description="PPTX下载URL")
    pdf_download_url: Optional[str] = Field(None, description="PDF下载URL")
    pdf_available: bool = Field(False, description="PDF版本是否可用")


class OutputFileListResponse(BaseModel):
    """输出文件列表响应"""
    success: bool = Field(..., description="是否成功")
    files: List[OutputFileInfo] = Field(default_factory=list, description="文件列表")
    total: int = Field(default=0, description="文件总数")
    message: str = Field(default="", description="响应消息")
