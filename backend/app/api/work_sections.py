"""
CRUD для разделов работ (WorkSection) — участки трубопровода/объекта с прогрессом.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.models.work_section import WorkSection, WorkSectionStatus as SectionStatus
from app.models.project import Project

router = APIRouter(prefix="/api/work-sections", tags=["work-sections"])


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class WorkSectionCreate(BaseModel):
    project_id: str
    name: str
    chainage_start: Optional[str] = None
    chainage_end: Optional[str] = None
    length_m: Optional[float] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    foreman: Optional[str] = None
    engineer: Optional[str] = None


class WorkSectionUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[SectionStatus] = None
    progress_pct: Optional[int] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    chainage_start: Optional[str] = None
    chainage_end: Optional[str] = None
    length_m: Optional[float] = None
    foreman: Optional[str] = None
    engineer: Optional[str] = None


class WorkSectionResponse(BaseModel):
    id: str
    project_id: str
    name: str
    status: SectionStatus
    progress_pct: int
    chainage_start: Optional[str]
    chainage_end: Optional[str]
    length_m: Optional[float]
    planned_start: Optional[date]
    planned_end: Optional[date]
    actual_start: Optional[date]
    actual_end: Optional[date]
    foreman: Optional[str]
    engineer: Optional[str]

    class Config:
        from_attributes = True


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/project/{project_id}", response_model=list[WorkSectionResponse])
async def list_sections(project_id: str, db: AsyncSession = Depends(get_db)):
    """Список разделов работ проекта."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    result = await db.execute(
        select(WorkSection)
        .where(WorkSection.project_id == project_id)
        .order_by(WorkSection.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=WorkSectionResponse, status_code=201)
async def create_section(body: WorkSectionCreate, db: AsyncSession = Depends(get_db)):
    """Создать раздел работ."""
    project = await db.get(Project, body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    section = WorkSection(**body.model_dump())
    db.add(section)
    await db.flush()
    await db.refresh(section)
    return section


@router.patch("/{section_id}", response_model=WorkSectionResponse)
async def update_section(section_id: str, body: WorkSectionUpdate, db: AsyncSession = Depends(get_db)):
    """Обновить статус / прогресс / исполнителей раздела работ."""
    section = await db.get(WorkSection, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Раздел работ не найден")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(section, field, value)
    await db.flush()
    await db.refresh(section)
    return section


@router.delete("/{section_id}", status_code=204)
async def delete_section(section_id: str, db: AsyncSession = Depends(get_db)):
    """Удалить раздел работ."""
    section = await db.get(WorkSection, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Раздел работ не найден")
    await db.delete(section)
