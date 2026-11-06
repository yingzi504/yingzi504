"""
Process API 端点 - Pipeline 步骤 2.10

提供任务提交、状态查询和结果获取的 REST API
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.task import (
    PipelineSubmitRequest,
    GenderInputRequest,
    TaskStatusResponse,
    TaskResultResponse,
    TaskListResponse,
)
from app.services.pipeline_service import PipelineService
from app.services.translator_service import normalize_target_language

router = APIRouter()


def _detect_job_position_language(value: str) -> Optional[str]:
    """Return CN/EN for a clearly Chinese or English target position."""
    return PipelineService.detect_target_position_language(value)


@router.post("/process")
async def submit_pipeline_task(request: PipelineSubmitRequest):
    """
    提交简历处理任务（Pipeline 全部步骤）

    提交后立即返回 task_id，任务在后台异步执行。
    前端通过轮询 GET /process/{task_id} 获取实时进度。

    处理流程:
      1. 文档解析 (PDF/Word → 文本)
      2. LLM结构化抽取 (文本 → ResumeData)
      3. 翻译+脱敏 (CN↔EN + 隐私保护)
      4. 约束性摘要 (经历优化)
      5. PPT模板填充 (生成最终简历)

    注意: 需要先通过 POST /api/v1/resume/upload 上传简历文件获取 file_id
    """
    try:
        normalized_target_language = normalize_target_language(
            request.target_language
        )
        normalized_template_language = (
            normalize_target_language(request.template_language)
            if request.template_language.strip()
            else ""
        )

        requested_position_language = _detect_job_position_language(request.job_position or "")
        output_language = (
            normalized_template_language or normalized_target_language
        )
        if requested_position_language and requested_position_language != output_language:
            raise HTTPException(
                status_code=400,
                detail="目标岗位语言必须与输出语言一致；请调整目标岗位或输出语言后再处理。"
            )

        # 创建任务
        task_id = PipelineService.create_task(
            file_id=request.file_id,
            template_type=request.template_type,
            target_language=normalized_target_language,
            job_position=request.job_position or "",
            template_language=normalized_template_language,
            department=request.department,
        )

        # 在后台启动 Pipeline 执行
        from app.services.access_service import register_resource, owned_resource, current_actor
        source_name = owned_resource(request.file_id).name if current_actor.get() else request.file_id
        register_resource(
            task_id,
            "cv",
            source_name,
            department=request.department,
            position=request.job_position or "",
        )
        PipelineService.start_pipeline(task_id)

        # 立即返回任务状态（包装为统一 {success, data, message} 格式）
        task = PipelineService.get_task(task_id)
        return {
            "success": True,
            "data": TaskStatusResponse(**task.to_status_dict()).model_dump(),
            "message": "任务提交成功",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.post("/process/{task_id}/gender")
async def provide_task_gender(task_id: str, request: GenderInputRequest):
    task = PipelineService.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "awaiting_input":
        raise HTTPException(status_code=409, detail="Task is not waiting for gender")
    try:
        task.gender_confirmation.confirm(request.gender)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    task.status = "pending"
    PipelineService.start_pipeline(task_id)
    return {"success": True, "data": TaskStatusResponse(**task.to_status_dict()).model_dump()}


@router.get("/process/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态（轮询用）

    返回当前进度、当前步骤名称和完成百分比。
    前端可每1-2秒轮询一次，直到 status 变为 completed 或 failed。

    status 枚举:
      - pending: 等待处理
      - processing: 处理中
      - completed: 已完成
      - failed: 失败
    """
    task = PipelineService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return {
        "success": True,
        "data": TaskStatusResponse(**task.to_status_dict()).model_dump(),
        "message": "获取成功",
    }


@router.get("/process/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务处理结果

    仅在任务完成后（status=completed）返回完整结果，包括:
      - 生成的文件名和下载链接
      - 处理后的简历数据 (ResumeData)
      - PPT验证结果
      - 各步骤耗时统计

    如果任务尚未完成，返回当前状态和进度。
    """
    task = PipelineService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return {
        "success": True,
        "data": TaskResultResponse(**task.to_result_dict()).model_dump(),
        "message": "获取成功",
    }


@router.get("/process", response_model=TaskListResponse)
async def list_tasks():
    """
    获取所有任务列表

    按创建时间倒序排列，用于历史记录查看
    """
    from app.services.access_service import visible_task_ids
    allowed = visible_task_ids()
    tasks = [task for task in PipelineService.get_all_tasks() if task.task_id in allowed]
    return TaskListResponse(
        tasks=[TaskStatusResponse(**t.to_status_dict()) for t in tasks],
        total=len(tasks),
    )


@router.get("/process/{task_id}/download")
async def download_task_output(task_id: str, format: str = "pptx"):
    from app.services.access_service import current_actor
    if current_actor.get():
        from app.api.access import download_record
        return download_record(task_id, format, current_actor.get())
    """
    下载任务输出文件

    支持 PPTX 和 PDF 两种格式。
    对应前端 downloadOutput() 调用。
    """
    task = PipelineService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成，无法下载")

    if not task.output_path or not os.path.exists(task.output_path):
        raise HTTPException(status_code=404, detail="输出文件不存在")

    # 确定要下载的文件路径
    if format == "pdf":
        # PDF 路径: 将 .pptx 替换为 .pdf
        pdf_path = task.output_path
        if pdf_path.endswith('.pptx'):
            pdf_path = pdf_path[:-5] + '.pdf'
        elif not pdf_path.endswith('.pdf'):
            pdf_path += '.pdf'

        if not os.path.exists(pdf_path):
            try:
                from app.services.pdf_converter import PdfConverterService
                pdf_path = PdfConverterService.ensure_pdf_for_pptx(
                    task.output_path, os.path.dirname(task.output_path)
                )
            except Exception as exc:
                raise HTTPException(status_code=404, detail=f"PDF 文件尚未生成，请检查 PDF 转换环境: {exc}") from exc
        file_path = pdf_path
        media_type = "application/pdf"
        download_name = task.output_filename.replace('.pptx', '.pdf') if task.output_filename else "output.pdf"
    else:
        file_path = task.output_path
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        download_name = task.output_filename or "output.pptx"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download_name,
    )
