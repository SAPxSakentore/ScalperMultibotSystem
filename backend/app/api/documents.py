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


class GenerateWeldingJournalRequest(BaseModel):
    project_id: str
    entries: Optional[List[Dict]] = None


class GenerateKS2Request(BaseModel):
    project_id: str
    period: Optional[str] = None
    contract_number: Optional[str] = None
    total_amount: Optional[str] = None
    works: Optional[List[Dict]] = None


class GeneratePurgeActRequest(BaseModel):
    project_id: str
    section_chainage: str
    length_m: Optional[float] = None
    purge_pressure_mpa: Optional[float] = None
    duration_min: Optional[int] = None
    purge_medium: Optional[str] = "сжатый воздух"
    dew_point: Optional[str] = "−20"
    result: Optional[str] = None
    date: Optional[str] = None
    foreman: Optional[str] = None


class UpdateDocumentStatusRequest(BaseModel):
    status: DocumentStatus
    signed_by: Optional[str] = None
    document_number: Optional[str] = None


class GeneratePPRRequest(BaseModel):
    project_id: str
    installation_method: Optional[str] = "открытая траншея"
    notes: Optional[str] = None


class GenerateTechCardRequest(BaseModel):
    project_id: str
    phase: str                         # значение ConstructionPhase enum
    card_number: Optional[int] = 1
    custom_scope: Optional[str] = ""


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


@router.post("/generate/ppr", response_model=DocumentResponse)
async def generate_ppr(request: GeneratePPRRequest, db: AsyncSession = Depends(get_db)):
    """Сгенерировать Проект производства работ (ППР)."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)

    options = {
        "installation_method": request.installation_method or "открытая траншея",
    }
    file_path = document_generator.generate_ppr(project_dict, options)

    doc = Document(
        project_id=project.id,
        document_type=DocumentType.PPR,
        title=f"ППР — {project.name}",
        file_path=file_path,
        file_format="docx",
        auto_generated=True,
        content_json=options,
        normative_refs=["СНиП РК 3.01.01-2008*", "СП РК 1.04.02-2019"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/tech-card", response_model=DocumentResponse)
async def generate_tech_card(request: GenerateTechCardRequest, db: AsyncSession = Depends(get_db)):
    """
    Сгенерировать технологическую карту на конкретный вид работ (фазу строительства).
    """
    from app.models.shift_report import ConstructionPhase, PHASE_NAMES_RU

    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)

    try:
        phase = ConstructionPhase(request.phase)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Неизвестная фаза: {request.phase}")

    file_path = document_generator.generate_tech_card(
        project_dict,
        phase_value=phase.value,
        card_number=request.card_number or 1,
        custom_scope=request.custom_scope or "",
    )

    from app.models.shift_report import PHASE_NAMES_RU
    doc = Document(
        project_id=project.id,
        document_type=DocumentType.TECH_CARD,
        title=f"ТК-{request.card_number:02d} — {PHASE_NAMES_RU[phase]}",
        file_path=file_path,
        file_format="docx",
        auto_generated=True,
        content_json={"phase": phase.value, "card_number": request.card_number},
        normative_refs=["СНиП РК 3.01.01-2008*"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/welding-journal", response_model=DocumentResponse)
async def generate_welding_journal(request: GenerateWeldingJournalRequest, db: AsyncSession = Depends(get_db)):
    """Сгенерировать Журнал производства сварочных работ."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)
    file_path = document_generator.generate_welding_journal(project_dict, request.entries or [])
    doc = Document(
        project_id=project.id,
        document_type=DocumentType.WELDING_JOURNAL,
        title=f"Журнал сварочных работ — {project.name}",
        file_path=file_path, file_format="docx", auto_generated=True,
        normative_refs=["ВСН 012-88", "РД РК 3.01.001-2019"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/ks2", response_model=DocumentResponse)
async def generate_ks2(request: GenerateKS2Request, db: AsyncSession = Depends(get_db)):
    """Сгенерировать Акт о приёмке выполненных работ (КС-2)."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)
    ks2_dict = request.model_dump(exclude={"project_id"})
    file_path = document_generator.generate_ks2(project_dict, ks2_dict)
    doc = Document(
        project_id=project.id,
        document_type=DocumentType.KS2,
        title=f"КС-2 Акт выполненных работ — {project.name}",
        file_path=file_path, file_format="docx", auto_generated=True,
        content_json=ks2_dict,
        normative_refs=["Приказ МФ РК", "СНиП РК 1.01.12-2009"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/generate/purge-act", response_model=DocumentResponse)
async def generate_purge_act(request: GeneratePurgeActRequest, db: AsyncSession = Depends(get_db)):
    """Сгенерировать Акт продувки и осушки газопровода."""
    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)
    purge_dict = request.model_dump(exclude={"project_id"})
    file_path = document_generator.generate_purge_act(project_dict, purge_dict)
    doc = Document(
        project_id=project.id,
        document_type=DocumentType.PURGE_ACT,
        title=f"Акт продувки — ПК {request.section_chainage}",
        file_path=file_path, file_format="docx", auto_generated=True,
        content_json=purge_dict,
        normative_refs=["СП РК 2.04-103-2013* п.10.5"],
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.patch("/{doc_id}/status", response_model=DocumentResponse)
async def update_document_status(
    doc_id: str,
    request: UpdateDocumentStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Обновить статус документа (черновик → проверка → согласован → подписан)."""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    doc.status = request.status
    if request.signed_by:
        doc.approved_by = request.signed_by
        doc.signed_date = datetime.utcnow()
    if request.document_number:
        doc.document_number = request.document_number
    doc.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(doc)
    return doc


@router.get("/phases")
async def list_phases():
    """Список фаз строительства (для выбора в техкарте)."""
    from app.models.shift_report import ConstructionPhase, PHASE_NAMES_RU
    return [
        {"value": phase.value, "label": PHASE_NAMES_RU[phase]}
        for phase in ConstructionPhase
    ]


class GenerateAllTechCardsRequest(BaseModel):
    project_id: str
    phases: Optional[List[str]] = None   # None = все 20 фаз


@router.post("/generate/tech-cards-bundle")
async def generate_tech_cards_bundle(
    request: GenerateAllTechCardsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Сформировать пакет технологических карт (все/выбранные фазы) и вернуть ZIP-архив.
    """
    import zipfile, io
    from app.models.shift_report import ConstructionPhase, PHASE_NAMES_RU
    from fastapi.responses import StreamingResponse

    project = await _get_project_or_404(request.project_id, db)
    project_dict = _project_to_dict(project)

    if request.phases:
        try:
            phases = [ConstructionPhase(p) for p in request.phases]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        phases = list(ConstructionPhase)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, phase in enumerate(phases, 1):
            file_path = document_generator.generate_tech_card(
                project_dict,
                phase_value=phase.value,
                card_number=i,
            )
            arc_name = f"ТК-{i:02d}_{phase.value}.docx"
            with open(file_path, "rb") as f:
                zf.writestr(arc_name, f.read())
            # Сохраняем запись в БД
            doc = Document(
                project_id=project.id,
                document_type=DocumentType.TECH_CARD,
                title=f"ТК-{i:02d} — {PHASE_NAMES_RU[phase]}",
                file_path=file_path,
                file_format="docx",
                auto_generated=True,
                content_json={"phase": phase.value, "card_number": i},
                normative_refs=["СНиП РК 3.01.01-2008*"],
                status=DocumentStatus.DRAFT,
            )
            db.add(doc)

    await db.flush()
    zip_buffer.seek(0)
    filename = f"TechCards_{project_dict.get('code', 'PROJ')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
