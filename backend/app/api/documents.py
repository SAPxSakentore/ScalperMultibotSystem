from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import asyncio
import os

from app.core.database import get_db
from app.models.project import Project
from app.models.document import Document, DocumentType, DocumentStatus
from app.agents import get_agent
from app.services.document_generator import document_generator

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    project_id: str
    document_type: DocumentType
    title: str
    content_json: Optional[Dict[str, Any]] = None
    normative_refs: Optional[List[str]] = None
    document_date: Optional[datetime] = None


class GenerateAOSRRequest(BaseModel):
    project_id: str
    work_name: str
    chainage: Optional[str] = None
    work_date: Optional[str] = None
    materials: Optional[List[str]] = None
    normatives: Optional[List[str]] = None
    foreman: Optional[str] = None
    author_supervisor: Optional[str] = None
    next_works: Optional[str] = None
    act_number: Optional[str] = None


class GenerateOJRRequest(BaseModel):
    project_id: str
    entries: Optional[List[Dict]] = None


class GenerateHydraulicTestRequest(BaseModel):
    project_id: str
    section_chainage: str
    length_m: float
    wall_thickness_mm: float
    steel_grade: str
    test_pressure_mpa: float
    tightness_pressure_mpa: float
    test_date: Optional[str] = None
    pressure_start: Optional[float] = None
    pressure_end: Optional[float] = None
    duration_hours: Optional[int] = 24
    result: Optional[str] = "УДОВЛЕТВОРИТЕЛЬНО"


class DocumentResponse(BaseModel):
    id: str
    project_id: str
    document_type: DocumentType
    document_number: Optional[str]
    title: str
    status: DocumentStatus
    file_path: Optional[str]
    auto_generated: bool
    document_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@router.get("/project/{project_id}", response_model=List[DocumentResponse])
async def list_documents(
    project_id: str,
    doc_type: Optional[DocumentType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получить список документов проекта."""
    query = select(Document).where(Document.project_id == project_id)
    if doc_type:
        query = query.where(Document.document_type == doc_type)
    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/generate/ojr", response_model=DocumentResponse)
async def generate_ojr(request: GenerateOJRRequest, db: AsyncSession = Depends(get_db)):
    """Сгенерировать Общий журнал работ (ОЖР)."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)

    file_path = document_generator.generate_ojr(project_dict, request.entries or [])

    doc = Document(
        project_id=project.id,
        document_type=DocumentType.OJR,
        title=f"Общий журнал работ — {project.name}",
        file_path=file_path,
        file_format="docx",
        auto_generated=True,
        normative_refs=["СП РК 1.04.02-2019"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/aosr", response_model=DocumentResponse)
async def generate_aosr(
    request: GenerateAOSRRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Сгенерировать АОСР (Акт освидетельствования скрытых работ)."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)
    work_dict = request.model_dump(exclude={"project_id"})

    file_path = document_generator.generate_aosr(project_dict, work_dict)

    doc = Document(
        project_id=project.id,
        document_type=DocumentType.AOSR,
        document_number=request.act_number,
        title=f"АОСР — {request.work_name}",
        file_path=file_path,
        file_format="docx",
        auto_generated=True,
        content_json=work_dict,
        normative_refs=request.normatives or ["СП РК 1.04.02-2019", "СП РК 2.04-103-2013*"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/hydraulic-test", response_model=DocumentResponse)
async def generate_hydraulic_test(
    request: GenerateHydraulicTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Сгенерировать Акт гидравлических испытаний."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)
    test_dict = request.model_dump(exclude={"project_id"})

    file_path = document_generator.generate_hydraulic_test_act(project_dict, test_dict)

    doc = Document(
        project_id=project.id,
        document_type=DocumentType.HYDRAULIC_TEST,
        title=f"Акт гидравлических испытаний — ПК {request.section_chainage}",
        file_path=file_path,
        file_format="docx",
        auto_generated=True,
        content_json=test_dict,
        normative_refs=["СП РК 2.04-103-2013*"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/ks11")
async def generate_ks11(project_id: str, db: AsyncSession = Depends(get_db)):
    """Сгенерировать Акт приемки объекта (КС-11)."""
    project = await _get_project_or_404(project_id, db)
    project_dict = _project_to_dict(project)

    file_path = document_generator.generate_ks11(project_dict)

    doc = Document(
        project_id=project.id,
        document_type=DocumentType.KS11,
        title=f"КС-11 Акт приемки — {project.name}",
        file_path=file_path,
        file_format="docx",
        auto_generated=True,
        normative_refs=["СНиП РК 1.01.12-2009", "Закон РК №242-II"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return {"document_id": doc.id, "file_path": file_path, "title": doc.title}


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    format: str = "docx",
    db: AsyncSession = Depends(get_db),
):
    """
    Скачать документ.
    ?format=docx  — исходный DOCX (по умолчанию)
    ?format=pdf   — PDF, сгенерированный на лету через ReportLab
    """
    from fastapi.responses import Response
    from app.services.pdf_generator import render_document_as_pdf

    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if format == "pdf":
        project = await db.get(Project, doc.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Проект не найден")

        project_dict = _project_to_dict(project)
        content = doc.content_json or {}

        pdf_bytes = render_document_as_pdf(
            doc_type=doc.document_type.value,
            project=project_dict,
            content=content,
        )

        safe_title = doc.title.replace("/", "-").replace("\\", "-")[:80]
        filename = f"{safe_title}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # DOCX
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Файл документа не найден")
    return FileResponse(doc.file_path, filename=os.path.basename(doc.file_path))


@router.post("/{doc_id}/check-with-ai")
async def check_document_with_ai(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Проверить документ через агента контроля качества."""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    project = await db.get(Project, doc.project_id)
    agent = get_agent("quality_control")
    project_dict = _project_to_dict(project)

    result = await agent.think(
        f"Проверь следующий документ на соответствие нормативам РК:\n"
        f"Тип: {doc.document_type.value}\n"
        f"Наименование: {doc.title}\n"
        f"Содержимое: {doc.content_json}",
        project_type=project.project_type.value
    )
    return {"document_id": doc_id, "review": result, "reviewed_by": agent.name_ru}


def _project_to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "project_type": project.project_type.value,
        "customer_name": project.customer_name,
        "contractor_name": project.contractor_name,
        "designer_name": project.designer_name,
        "technical_supervisor": project.technical_supervisor,
        "region": project.region,
        "diameter_mm": project.diameter_mm,
        "total_length_km": project.total_length_km,
        "working_pressure_mpa": project.working_pressure_mpa,
        "start_date": str(project.start_date) if project.start_date else None,
        "actual_end_date": str(project.actual_end_date) if project.actual_end_date else None,
    }
