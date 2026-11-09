import asyncio
from typing import Optional
import urllib.parse
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from datetime import datetime
import os
import uuid
from pathlib import Path

from app.schemas.parser import ParseRequest, ParseResponse, ParseResult
from app.schemas.resume import (
    ExtractionRequest, ExtractionResponse, ResumeData,
    TranslationRequest, TranslationResponse,
    AnonymizationRequest, AnonymizationResponse,
    TransformRequest, TransformResponse,
    SummarizationRequest, SummarizationResponse,
    FillerRequest, FillerResponse,
    OutputFileInfo, OutputFileListResponse,
)
from app.services.parser_service import ParserService
from app.services.extractor_service import ExtractorService
from app.services.translator_service import (
    TranslationQualityError,
    TranslatorService,
    normalize_target_language,
)
from app.services.anonymizer_service import AnonymizerService
from app.services.summarization_service import SummarizationService
from app.services.smart_filler_service import SmartFillerService
from app.services.pptx_validator import validate_pptx, print_validation_report
from app.core.config import settings
from app.core.cv_rules import cv_download_filename
from app.core.cache import output_list_cache  # 步骤4.8: TTL 缓存

router = APIRouter()

# 上传/输出目录配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = str(settings.upload_path)
OUTPUT_DIR = str(settings.output_path)

# 仅允许的简历文件格式（upload端点使用，排除图片格式）
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".doc"}

# 最大上传字节数
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    上传简历文件
    
    支持格式: PDF, DOCX, DOC (最多 {max_size_mb}MB)
    """
    try:
        # ── 1. 文件类型验证 ──
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式 '{ext}'。支持格式: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
            )
        
        # ── 2. 文件大小验证 (读取内容同时检查大小) ──
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_UPLOAD_BYTES:
            size_mb = file_size / (1024 * 1024)
            limit_mb = settings.max_upload_size_mb
            raise HTTPException(
                status_code=400,
                detail=f"文件大小 ({size_mb:.1f}MB) 超出限制 ({limit_mb}MB)"
            )
        if file_size == 0:
            raise HTTPException(status_code=400, detail="文件为空，请上传有效文件")
        
        # ── 3. 保存文件 ──
        file_id = str(uuid.uuid4())
        unique_filename = f"{file_id}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        from app.services.access_service import register_resource
        register_resource(file_id, "upload", file.filename, {ext[1:]: file_path})
        
        return {
            "success": True,
            "data": {
                "file_id": file_id,
                "original_filename": file.filename,
                "saved_filename": unique_filename,
                "file_size": file_size,
                "file_size_display": f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB",
            },
            "message": "文件上传成功",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/parse", response_model=ParseResponse)
async def parse_resume(request: ParseRequest):
    """
    解析已上传的简历文件（Pipeline 步骤 1）
    
    使用 unstructured + PaddleOCR 提取文本内容
    """
    try:
        # 查找文件
        upload_files = os.listdir(UPLOAD_DIR)
        target_file = None
        original_filename = None
        
        for f in upload_files:
            if f.startswith(request.file_id):
                target_file = os.path.join(UPLOAD_DIR, f)
                original_filename = f
                break
        
        if not target_file or not os.path.exists(target_file):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 调用解析服务
        parse_result_dict = await ParserService.parse_file(target_file, original_filename)
        parse_result = ParseResult(**parse_result_dict)
        
        return ParseResponse(
            success=True,
            data=parse_result,
            message="文件解析成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return ParseResponse(
            success=False,
            data=None,
            message=f"文件解析失败: {str(e)}"
        )


@router.post("/upload-and-parse", response_model=ParseResponse)
async def upload_and_parse_resume(file: UploadFile = File(...)):
    """
    上传并立即解析简历（Pipeline 步骤 1 快捷方式）
    
    一步完成文件上传和文本解析
    """
    try:
        # 上传文件
        upload_result = await upload_resume(file)
        file_id = upload_result["data"]["file_id"]
        original_filename = upload_result["data"]["original_filename"]
        
        # 查找保存的文件
        upload_files = os.listdir(UPLOAD_DIR)
        target_file = None
        for f in upload_files:
            if f.startswith(file_id):
                target_file = os.path.join(UPLOAD_DIR, f)
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="文件保存失败")
        
        # 解析文件
        parse_result_dict = await ParserService.parse_file(target_file, original_filename)
        parse_result = ParseResult(**parse_result_dict)
        
        return ParseResponse(
            success=True,
            data=parse_result,
            message="文件上传并解析成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return ParseResponse(
            success=False,
            data=None,
            message=f"处理失败: {str(e)}"
        )


@router.post("/extract", response_model=ExtractionResponse)
async def extract_resume(request: ExtractionRequest):
    """
    从文本中抽取结构化简历信息（Pipeline 步骤 2）
    
    使用 LLM 进行智能结构化信息抽取
    """
    try:
        if not request.raw_text or not request.raw_text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # 调用信息抽取服务
        resume_data = await ExtractorService.extract_structure(request.raw_text)
        # Keep the diagnostic endpoint structurally aligned with /process.
        # Deterministic source recovery prevents a replay from returning fewer
        # work/project entries than the authoritative pipeline.
        resume_data = SummarizationService.recover_work_history(
            resume_data, request.raw_text
        )
        resume_data = SummarizationService.recover_embedded_projects(
            resume_data, request.raw_text
        )
        
        return ExtractionResponse(
            success=True,
            data=resume_data,
            message="信息抽取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return ExtractionResponse(
            success=False,
            data=None,
            message=f"信息抽取失败: {str(e)}"
        )


@router.post("/parse-and-extract", response_model=ExtractionResponse)
async def parse_and_extract_resume(request: ParseRequest):
    """
    解析文件并抽取结构化信息（Pipeline 步骤 1+2 快捷方式）
    
    一步完成文档解析和信息抽取
    """
    try:
        # 先解析文件
        parse_response = await parse_resume(request)
        
        if not parse_response.success or not parse_response.data:
            raise HTTPException(status_code=400, detail="文件解析失败")
        
        # 再抽取信息
        extraction_request = ExtractionRequest(raw_text=parse_response.data.text_content)
        extraction_response = await extract_resume(extraction_request)
        
        return extraction_response
        
    except HTTPException:
        raise
    except Exception as e:
        return ExtractionResponse(
            success=False,
            data=None,
            message=f"处理失败: {str(e)}"
        )


def _resolve_target_language(
    target_language: Optional[str],
    template_language: Optional[str],
) -> Optional[str]:
    """解析翻译目标语言：优先使用 template_language，其次使用 target_language"""
    normalized_target = (
        normalize_target_language(target_language)
        if target_language is not None
        else None
    )
    normalized_template = (
        normalize_target_language(template_language)
        if template_language is not None
        else None
    )
    if normalized_template:
        return normalized_template
    if normalized_target:
        return normalized_target
    return normalize_target_language(None)


@router.post("/translate", response_model=TranslationResponse)
async def translate_resume(request: TranslationRequest):
    """
    翻译简历（Pipeline 步骤 3 的一部分）
    
    将简历翻译为目标语言（中文↔英文）。如果提供了 template_language，则优先使用作为翻译目标语言。
    """
    try:
        final_target_lang = _resolve_target_language(
            request.target_language, request.template_language
        )
        if not final_target_lang:
            raise HTTPException(status_code=400, detail="必须提供 target_language 或 template_language")
        
        translated_data = await TranslatorService.translate_resume(
            request.resume_data,
            final_target_lang
        )
        
        return TranslationResponse(
            success=True,
            data=translated_data,
            message="翻译成功"
        )
        
    except TranslationQualityError as e:
        raise HTTPException(status_code=422, detail=e.to_detail()) from e
    except HTTPException:
        raise
    except Exception as e:
        return TranslationResponse(
            success=False,
            data=None,
            message=f"翻译失败: {str(e)}"
        )


@router.post("/anonymize", response_model=AnonymizationResponse)
async def anonymize_resume(request: AnonymizationRequest):
    """
    脱敏简历（Pipeline 步骤 3 的一部分）
    
    移除个人敏感信息（电话、邮箱、年龄、地点）
    姓名自动推断性别 → Mr./Ms. 姓（英文）或 姓先生/女士（中文）
    保留公司名不变
    """
    try:
        anonymized_data = AnonymizerService.anonymize_resume(request.resume_data)
        
        return AnonymizationResponse(
            success=True,
            data=anonymized_data,
            message="脱敏成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return AnonymizationResponse(
            success=False,
            data=None,
            message=f"脱敏失败: {str(e)}"
        )


@router.post("/transform", response_model=TransformResponse)
async def transform_resume(request: TransformRequest):
    """
    翻译+脱敏联合处理（Pipeline 步骤 3）
    
    一步完成翻译和脱敏处理。如果提供了 template_language，则优先使用作为翻译目标语言。
    """
    try:
        result_data = request.resume_data.model_copy(deep=True)
        
        final_target_lang = _resolve_target_language(
            request.target_language, request.template_language
        )
        
        # 1. 翻译（如果需要）
        if final_target_lang:
            result_data = await TranslatorService.translate_resume(
                result_data,
                final_target_lang
            )
        
        # 2. 脱敏（如果需要）
        if request.perform_anonymization:
            result_data = AnonymizerService.anonymize_resume(result_data)
        
        return TransformResponse(
            success=True,
            data=result_data,
            message="处理成功"
        )
        
    except TranslationQualityError as e:
        raise HTTPException(status_code=422, detail=e.to_detail()) from e
    except HTTPException:
        raise
    except Exception as e:
        return TransformResponse(
            success=False,
            data=None,
            message=f"处理失败: {str(e)}"
        )


@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_resume(request: SummarizationRequest):
    """
    摘要优化简历（Pipeline 步骤 4）
    
    优化简历经历描述：修正语法、统一格式、删除冗余、统一句式
    """
    try:
        summarized_data = await SummarizationService.summarize_resume(request.resume_data)
        
        return SummarizationResponse(
            success=True,
            data=summarized_data,
            message="摘要优化成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return SummarizationResponse(
            success=False,
            data=None,
            message=f"摘要优化失败: {str(e)}"
        )


@router.post("/fill", response_model=FillerResponse)
async def fill_template(request: FillerRequest):
    """
    PPT模板智能填充（推荐）- Pipeline 步骤 6
    
    ✨ 自动克隆表格行，支持多条工作/项目/教育经历
    ✨ 自动调整行高，根据内容自适应
    ✨ 填充后自动验证PPT (重叠/溢出/间距检查)
    ✨ 自动生成PDF版本 (需安装LibreOffice)
    ✨ 输出文件自动命名: IAV_{anonymized_name}_{position}_Resume_{language}
    
    将简历数据填入PPT模板并生成最终文件
    """
    try:
        # 使用智能填充 (返回 dict: pptx_path, pdf_path, filename)
        result = await asyncio.to_thread(
                SmartFillerService.fill_template,
            request.resume_data,
            orientation=request.template_type,
            generate_pdf=request.generate_pdf,
        )
        
        pptx_path = result["pptx_path"]
        pdf_path = result.get("pdf_path")
        filename = result["filename"]
        storage_filename = os.path.basename(pptx_path)
        pdf_available = pdf_path is not None and os.path.exists(pdf_path)
        
        # ── 验证生成的PPT ──
        validation_result = validate_pptx(pptx_path)
        validation_dict = validation_result.to_dict()
        
        # 打印报告到控制台
        print_validation_report(validation_result)
        
        # 计算文件大小和下载URL
        file_size = os.path.getsize(pptx_path) if os.path.exists(pptx_path) else None
        pdf_file_size = os.path.getsize(pdf_path) if pdf_available else None
        pptx_download_url = f"/api/v1/resume/fill/download/{urllib.parse.quote(storage_filename)}?format=pptx"
        pdf_download_url = (
            f"/api/v1/resume/fill/download/{urllib.parse.quote(storage_filename)}?format=pdf"
            if pdf_available else None
        )
        
        def _make_response(msg: str, needs_fix: bool = False) -> FillerResponse:
            return FillerResponse(
                success=True,
                output_path=pptx_path,
                filename=filename,
                pptx_download_url=pptx_download_url,
                pdf_download_url=pdf_download_url,
                file_size=file_size,
                pdf_file_size=pdf_file_size,
                pdf_available=pdf_available,
                message=msg,
                validation=validation_dict,
                needs_fix=needs_fix,
            )
        
        if validation_result.is_valid:
            return _make_response("PPT智能填充成功 ✅")
        else:
            return _make_response(
                f"PPT填充完成，但验证发现 {validation_result.error_count} 个问题需要修复 ⚠️",
                needs_fix=True,
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        return FillerResponse(
            success=False,
            output_path=None,
            filename=None,
            pptx_download_url=None,
            pdf_download_url=None,
            file_size=None,
            pdf_file_size=None,
            pdf_available=False,
            message=f"PPT填充失败: {str(e)}",
            validation=None,
            needs_fix=False,
        )


@router.get("/fill/download/{filename}")
async def download_filled_ppt(filename: str, format: str = "pptx"):
    """
    下载填充后的文件 (PPTX 或 PDF)
    
    - **filename**: 输出文件名 (如 `IAV_Mr.Zhang_Software_Resume_EN.pptx`)
    - **format**: 下载格式, 可选 `pptx` (默认) 或 `pdf`
    - 支持中文文件名, 自动设置正确的 Content-Disposition 头
    """
    try:
        # 确定文件扩展名和 MIME 类型
        if format == "pdf":
            # PDF: 将 .pptx 换成 .pdf
            pdf_filename = filename
            if pdf_filename.endswith('.pptx'):
                pdf_filename = pdf_filename[:-5] + '.pdf'
            elif not pdf_filename.endswith('.pdf'):
                pdf_filename += '.pdf'
            
            file_path = os.path.join(OUTPUT_DIR, pdf_filename)
            media_type = "application/pdf"
        elif format == "pptx":
            file_path = os.path.join(OUTPUT_DIR, filename)
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {format}，仅支持 pptx 或 pdf")
        
        if not os.path.exists(file_path):
            ext_name = "PDF" if format == "pdf" else "PPTX"
            raise HTTPException(
                status_code=404,
                detail=f"{ext_name} 文件不存在: {os.path.basename(file_path)}。"
                       f"{'请确认 LibreOffice 已安装以生成 PDF。' if format == 'pdf' else ''}"
            )
        
        # RFC 5987: 对中文文件名进行 URL 编码
        download_name = cv_download_filename(os.path.basename(file_path))
        encoded_filename = urllib.parse.quote(download_name, safe='')
        
        return FileResponse(
            path=file_path,
            filename=download_name,
            media_type=media_type,
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": (
                    f"attachment; filename*=UTF-8''{encoded_filename}"
                ),
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")


@router.get("/fill/info/{filename}", response_model=OutputFileInfo)
async def get_fill_file_info(filename: str):
    """
    获取填充后文件的元信息 (PPTX + PDF)
    
    - **filename**: PPTX文件名
    - 返回: 文件大小、创建时间、修改时间、PPTX/PDF下载URL
    """
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
        
        stat = os.stat(file_path)
        size_bytes = stat.st_size
        
        # 可读的文件大小
        if size_bytes < 1024:
            size_display = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_display = f"{size_bytes / 1024:.1f} KB"
        else:
            size_display = f"{size_bytes / (1024 * 1024):.2f} MB"
        
        # 检查 PDF 版本是否存在
        pdf_filename = filename
        if pdf_filename.endswith('.pptx'):
            pdf_filename = pdf_filename[:-5] + '.pdf'
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
        pdf_available = os.path.exists(pdf_path)
        
        return OutputFileInfo(
            filename=filename,
            size=size_bytes,
            size_display=size_display,
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            pptx_download_url=f"/api/v1/resume/fill/download/{urllib.parse.quote(filename)}?format=pptx",
            pdf_download_url=(
                f"/api/v1/resume/fill/download/{urllib.parse.quote(filename)}?format=pdf"
                if pdf_available else None
            ),
            pdf_available=pdf_available,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@router.get("/fill/outputs", response_model=OutputFileListResponse)
async def list_fill_outputs():
    """
    列出所有填充生成的输出文件 (仅PPTX, 每个含对应的PDF下载链接)
    
    - 按修改时间倒序排列
    - 返回: 文件列表及PPTX/PDF下载链接
    - 步骤4.8: 5分钟 TTL 缓存，减少磁盘 IO
    """
    # 尝试从缓存读取
    cached = output_list_cache.get("outputs")
    if cached is not None:
        return cached

    try:
        files = []
        if os.path.exists(OUTPUT_DIR):
            # 步骤4.8: 只 stat 一次（sorted key 复用）
            entries = []
            for entry in Path(OUTPUT_DIR).iterdir():
                if entry.is_file() and entry.suffix.lower() in ('.pptx', '.ppt'):
                    stat = entry.stat()
                    entries.append((stat.st_mtime, entry, stat))
            entries.sort(key=lambda x: x[0], reverse=True)

            for _, entry, stat in entries:
                size_bytes = stat.st_size
                
                if size_bytes < 1024:
                    size_display = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_display = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_display = f"{size_bytes / (1024 * 1024):.2f} MB"
                
                # 检查是否有对应的 PDF
                pdf_name = entry.stem + '.pdf'
                pdf_path = os.path.join(OUTPUT_DIR, pdf_name)
                pdf_available = os.path.exists(pdf_path)
                
                files.append(OutputFileInfo(
                    filename=entry.name,
                    size=size_bytes,
                    size_display=size_display,
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    pptx_download_url=f"/api/v1/resume/fill/download/{urllib.parse.quote(entry.name)}?format=pptx",
                    pdf_download_url=(
                        f"/api/v1/resume/fill/download/{urllib.parse.quote(entry.name)}?format=pdf"
                        if pdf_available else None
                    ),
                    pdf_available=pdf_available,
                ))
        
        result = OutputFileListResponse(
            success=True,
            files=files,
            total=len(files),
            message=f"共找到 {len(files)} 个输出文件",
        )

        # 写入缓存
        output_list_cache.set("outputs", result)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.get("/download/{file_id}")
async def download_resume(file_id: str):
    """下载处理后的简历"""
    raise HTTPException(status_code=501, detail="功能开发中")
