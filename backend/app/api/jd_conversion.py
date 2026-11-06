from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.jd_conversion import (
    JDConversionRequest,
    JDLocationRequest,
    JDPositionRecognitionRequest,
    JDRegenerateRequest,
)
from app.services.jd_conversion_service import JDConversionService
from app.services.jd_service import JDService


router = APIRouter()


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


@router.post("/recognize-position")
async def recognize_target_position(request: JDPositionRecognitionRequest):
    try:
        target_position = await JDConversionService.recognize_target_position(request)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _ok(
        {
            "target_position": target_position,
            "target_position_source": request.target_position_source,
        },
        "Target position recognized",
    )


@router.post("/tasks")
async def create_conversion_task(request: JDConversionRequest):
    task = JDConversionService.create_task(request)
    from app.services.access_service import register_resource
    register_resource(task.task_id, "jd", request.original_filename or request.target_position or "JD")
    JDConversionService.start_task(task.task_id)
    return _ok(task.status_dict(), "JD conversion task created")


@router.get("/tasks/{task_id}")
async def get_conversion_task(task_id: str):
    task = JDConversionService.get_task(task_id)
    if not task:
        raise HTTPException(404, "JD conversion task not found")
    return _ok(task.status_dict())


@router.put("/tasks/{task_id}")
async def regenerate_conversion_task(task_id: str, request: JDRegenerateRequest):
    task = JDConversionService.get_task(task_id)
    if not task:
        raise HTTPException(404, "JD conversion task not found")
    try:
        await JDConversionService.regenerate(task, request.content)
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        raise HTTPException(422, f"JD regeneration failed: {exc}") from exc
    finally:
        from app.services.access_service import persist_task
        persist_task(task, "jd")
    return _ok(task.status_dict(), "JD output regenerated")


@router.post("/tasks/{task_id}/location")
async def provide_conversion_location(task_id: str, request: JDLocationRequest):
    task = JDConversionService.get_task(task_id)
    if not task:
        raise HTTPException(404, "JD conversion task not found")
    try:
        await JDConversionService.provide_location(task, request.location)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        raise HTTPException(422, f"JD location update failed: {exc}") from exc
    finally:
        from app.services.access_service import persist_task
        persist_task(task, "jd")
    return _ok(task.status_dict(), "Work location supplied and JD generation resumed")


@router.get("/tasks/{task_id}/download")
async def download_conversion_output(
    task_id: str,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
):
    from app.services.access_service import current_actor
    if current_actor.get():
        from app.api.access import download_record
        return download_record(task_id, format, current_actor.get())
    task = JDConversionService.get_task(task_id)
    if not task:
        raise HTTPException(404, "JD conversion task not found")
    if task.status != "completed":
        raise HTTPException(400, "JD conversion task is not completed")

    file_path = Path(task.pdf_path if format == "pdf" else task.docx_path or "")
    if not file_path.exists():
        raise HTTPException(404, f"{format.upper()} output is not available")
    media_type = (
        "application/pdf"
        if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(file_path, media_type=media_type, filename=file_path.name)


@router.post("/tasks/{task_id}/save")
async def save_conversion_to_library(task_id: str, db: Session = Depends(get_db)):
    task = JDConversionService.get_task(task_id)
    if not task or task.status != "completed" or not task.content:
        raise HTTPException(400, "Only a completed JD conversion can be saved")
    item = JDService.save_final_conversion(db, task)
    return _ok(item, "Final JD saved to library")
