from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.project import Project, ProjectType, ProjectStatus
from app.models.shift_report import ShiftReport, ConstructionPhase, PHASE_NAMES_RU
from app.agents import get_agent
from app.services.normative_base import ITD_CHECKLISTS

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    project_type: ProjectType
    region: Optional[str] = None
    district: Optional[str] = None
    locality: Optional[str] = None
    total_length_km: Optional[float] = None
    diameter_mm: Optional[float] = None
    working_pressure_mpa: Optional[float] = None
    design_pressure_mpa: Optional[float] = None
    customer_name: Optional[str] = None
    customer_bin: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_bin: Optional[str] = None
    designer_name: Optional[str] = None
    technical_supervisor: Optional[str] = None
    design_doc_number: Optional[str] = None
    permit_number: Optional[str] = None
    start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    region: Optional[str] = None
    customer_name: Optional[str] = None
    contractor_name: Optional[str] = None
    technical_supervisor: Optional[str] = None
    permit_number: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    code: str
    name: str
    project_type: ProjectType
    status: ProjectStatus
    region: Optional[str]
    customer_name: Optional[str]
    contractor_name: Optional[str]
    total_length_km: Optional[float]
    diameter_mm: Optional[float]
    working_pressure_mpa: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Создать новый строительный проект."""
    # Проверить уникальность кода
    existing = await db.execute(select(Project).where(Project.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Проект с шифром '{data.code}' уже существует")

    project = Project(**data.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[ProjectStatus] = None,
    project_type: Optional[ProjectType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получить список проектов."""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    if project_type:
        query = query.where(Project.project_type == project_type)
    query = query.order_by(Project.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Получить проект по ID."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    """Обновить проект."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    project.updated_at = datetime.utcnow()
    return project


@router.get("/{project_id}/itd-checklist")
async def get_itd_checklist(project_id: str, db: AsyncSession = Depends(get_db)):
    """Получить чеклист ИТД для проекта."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    checklist = ITD_CHECKLISTS.get(project.project_type.value, [])
    return {"project_id": project_id, "project_type": project.project_type, "checklist": checklist}


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Удалить проект (каскадно удаляет документы и рапорты)."""
    from sqlalchemy import delete as sql_delete
    from app.models.document import Document
    from app.models.shift_report import ShiftReport, ProjectPdfUpload
    import os

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # Удалить файлы документов
    docs_result = await db.execute(select(Document).where(Document.project_id == project_id))
    for doc in docs_result.scalars().all():
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)

    # Удалить PDF-загрузки
    pdfs_result = await db.execute(select(ProjectPdfUpload).where(ProjectPdfUpload.project_id == project_id))
    for pdf in pdfs_result.scalars().all():
        if pdf.file_path and os.path.exists(pdf.file_path):
            os.remove(pdf.file_path)

    await db.execute(sql_delete(Document).where(Document.project_id == project_id))
    await db.execute(sql_delete(ShiftReport).where(ShiftReport.project_id == project_id))
    await db.execute(sql_delete(ProjectPdfUpload).where(ProjectPdfUpload.project_id == project_id))
    await db.delete(project)


@router.get("/{project_id}/export-itd")
async def export_project_itd(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Экспорт полного пакета ИТД проекта в ZIP-архив.
    Включает все сгенерированные DOCX-файлы.
    """
    import zipfile, io
    from fastapi.responses import StreamingResponse
    from app.models.document import Document
    import os

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    docs_result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .where(Document.file_path.isnot(None))
        .order_by(Document.document_type, Document.created_at)
    )
    docs = docs_result.scalars().all()

    zip_buffer = io.BytesIO()
    added = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            if doc.file_path and os.path.exists(doc.file_path):
                safe_title = doc.title.replace("/", "-").replace("\\", "-")[:60]
                arc_name = f"{doc.document_type.value}/{safe_title}.docx"
                with open(doc.file_path, "rb") as f:
                    zf.writestr(arc_name, f.read())
                added += 1

    if added == 0:
        raise HTTPException(status_code=404, detail="В проекте нет сгенерированных документов")

    zip_buffer.seek(0)
    filename = f"ITD_{project.code}_{datetime.now().strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{project_id}/generate-plan")
async def generate_project_plan(project_id: str, db: AsyncSession = Depends(get_db)):
    """Сгенерировать план реализации проекта через PM-агента."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    agent = get_agent("project_manager")
    project_dict = {
        "name": project.name,
        "code": project.code,
        "project_type": project.project_type.value,
        "total_length_km": project.total_length_km,
        "diameter_mm": project.diameter_mm,
        "working_pressure_mpa": project.working_pressure_mpa,
        "customer_name": project.customer_name,
        "contractor_name": project.contractor_name,
        "region": project.region,
    }
    plan = await agent.create_project_plan(project_dict)
    return {"project_id": project_id, "plan": plan, "generated_by": agent.name_ru}


@router.get("/{project_id}/progress")
async def get_project_progress(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Прогресс строительства по фазам.
    Агрегирует сменные рапорты: сумма метров, кол-во смен, последняя дата.
    Возвращает фазы в порядке технологической последовательности.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # Агрегация по фазам
    result = await db.execute(
        select(
            ShiftReport.construction_phase,
            func.sum(ShiftReport.length_done_m).label("length_done_m"),
            func.count(ShiftReport.id).label("shifts_count"),
            func.max(ShiftReport.shift_date).label("last_date"),
            func.sum(
                func.cast(ShiftReport.is_finalized, float)
            ).label("finalized_count"),
        )
        .where(ShiftReport.project_id == project_id)
        .group_by(ShiftReport.construction_phase)
    )
    rows = result.all()

    # Итого по проекту (в метрах)
    total_m = (project.total_length_km or 0) * 1000
    overall_done_m = sum(r.length_done_m or 0 for r in rows)

    # Собираем по порядку фаз из enum
    phase_index = {phase: i for i, phase in enumerate(ConstructionPhase)}
    row_map = {r.construction_phase: r for r in rows}

    phases_out = []
    for phase in ConstructionPhase:
        r = row_map.get(phase)
        done_m = float(r.length_done_m or 0) if r else 0.0
        pct = round(done_m / total_m * 100, 1) if total_m > 0 else None
        phases_out.append({
            "phase": phase.value,
            "name_ru": PHASE_NAMES_RU[phase],
            "length_done_m": done_m,
            "length_done_km": round(done_m / 1000, 3),
            "shifts_count": int(r.shifts_count) if r else 0,
            "finalized_count": int(r.finalized_count or 0) if r else 0,
            "last_date": r.last_date.isoformat() if r and r.last_date else None,
            "pct_of_total": pct,
            "has_data": r is not None,
        })

    return {
        "project_id": project_id,
        "total_length_km": project.total_length_km,
        "total_length_m": total_m,
        "overall_done_m": round(overall_done_m, 1),
        "overall_done_km": round(overall_done_m / 1000, 3),
        "overall_pct": round(overall_done_m / total_m * 100, 1) if total_m > 0 else None,
        "phases": phases_out,
    }


@router.post("/{project_id}/analyze-risks")
async def analyze_project_risks(project_id: str, db: AsyncSession = Depends(get_db)):
    """Анализ рисков проекта через PM-агента."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    agent = get_agent("project_manager")
    project_dict = {
        "name": project.name,
        "project_type": project.project_type.value,
        "region": project.region,
    }
    analysis = await agent.analyze_risks(project_dict)
    return {"project_id": project_id, "risks": analysis, "generated_by": agent.name_ru}
