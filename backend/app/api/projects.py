from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.project import Project, ProjectType, ProjectStatus
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
