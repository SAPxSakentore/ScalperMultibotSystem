"""
API сменных рапортов и загрузки PDF-документов проекта.

Маршруты:
  POST   /api/shift-reports/projects/{project_id}/upload-pdf
  GET    /api/shift-reports/projects/{project_id}/pdfs
  DELETE /api/shift-reports/projects/{project_id}/pdfs/{upload_id}

  GET    /api/shift-reports/phases                       — список фаз МГ
  POST   /api/shift-reports/                            — создать рапорт (вручную или AI)
  GET    /api/shift-reports/projects/{project_id}/       — рапорты проекта
  GET    /api/shift-reports/{report_id}
  PATCH  /api/shift-reports/{report_id}
  DELETE /api/shift-reports/{report_id}
  GET    /api/shift-reports/{report_id}/download         — PDF рапорта
"""
import os
import uuid
from datetime import datetime
from typing import List, Optional

import aiofiles
from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, UploadFile,
)
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.models.project import Project
from app.models.shift_report import (
    ConstructionPhase,
    PHASE_NAMES_RU,
    PHASE_NORMATIVES,
    PHASE_TYPICAL_MACHINERY,
    ProjectPdfUpload,
    ShiftNumber,
    ShiftReport,
)
from app.services.pdf_extractor import (
    detect_phases_in_text,
    extract_project_parameters,
    extract_text_from_bytes,
)
from app.services.shift_report_service import (
    generate_shift_report_with_ai,
    get_pdf_context_for_phase,
    summarize_pdf_with_ai,
)

router = APIRouter(prefix="/api/shift-reports", tags=["shift-reports"])

_PDF_UPLOAD_DIR = os.path.join(settings.DOCS_STORAGE_PATH, "project_pdfs")
os.makedirs(_PDF_UPLOAD_DIR, exist_ok=True)


# ── Вспомогательные функции ──────────────────────────────────────────────────

async def _get_project(db: AsyncSession, project_id: str) -> Project:
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")
    return proj


def _project_dict(p: Project) -> dict:
    return {
        "id": p.id, "code": p.code, "name": p.name,
        "customer_name": p.customer_name,
        "contractor_name": p.contractor_name,
        "designer_name": p.designer_name,
        "technical_supervisor": p.technical_supervisor,
        "diameter_mm": p.diameter_mm,
        "working_pressure_mpa": p.working_pressure_mpa,
        "total_length_km": p.total_length_km,
        "region": p.region,
    }


def _report_to_dict(r: ShiftReport) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "shift_date": r.shift_date.isoformat() if r.shift_date else None,
        "shift_number": r.shift_number.value if r.shift_number else "day",
        "shift_foreman": r.shift_foreman,
        "construction_phase": r.construction_phase.value if r.construction_phase else None,
        "chainage_start": r.chainage_start,
        "chainage_end": r.chainage_end,
        "length_done_m": r.length_done_m,
        "weather_morning": r.weather_morning,
        "weather_afternoon": r.weather_afternoon,
        "works_done": r.works_done or [],
        "workers_on_site": r.workers_on_site or {},
        "machinery_on_site": r.machinery_on_site or [],
        "materials_received": r.materials_received or [],
        "quality_checks": r.quality_checks or [],
        "downtime_hours": r.downtime_hours,
        "downtime_reason": r.downtime_reason,
        "safety_incidents": r.safety_incidents,
        "documents_issued": r.documents_issued or [],
        "next_shift_plan": r.next_shift_plan,
        "ai_generated": r.ai_generated,
        "is_finalized": r.is_finalized,
        "signed_by": r.signed_by,
        "signed_at": r.signed_at.isoformat() if r.signed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ════════════════════════════════════════════════════════════════════════════
#  PDF ЗАГРУЗКА
# ════════════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/upload-pdf", summary="Загрузить PDF документ проекта")
async def upload_project_pdf(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_category: str = Form("прочее"),
    db: AsyncSession = Depends(get_db),
):
    """
    Загрузить PDF-документ проекта (ПОС, ППР, ПД, НТД и т.д.).
    Автоматически извлекается текст, определяются фазы строительства.
    Краткое содержание формируется через AI в фоне.
    """
    proj = await _get_project(db, project_id)

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Разрешены только файлы формата PDF")

    # Сохранить файл
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(_PDF_UPLOAD_DIR, safe_name)
    content = await file.read()

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Извлечь текст
    try:
        text, page_count = extract_text_from_bytes(content)
    except RuntimeError as exc:
        os.remove(file_path)
        raise HTTPException(422, str(exc))

    phases = detect_phases_in_text(text)
    params = extract_project_parameters(text)

    upload = ProjectPdfUpload(
        project_id=project_id,
        filename=file.filename,
        file_path=file_path,
        doc_category=doc_category,
        page_count=page_count,
        extracted_text=text,
        text_summary="",  # заполнится в фоне
        construction_phases_mentioned=[p.value for p in phases],
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    # AI-суммаризация в фоне (новая независимая сессия)
    async def _summarize(upload_id: str, filename: str, text_: str):
        async with AsyncSessionLocal() as session:
            u = await session.get(ProjectPdfUpload, upload_id)
            if u:
                u.text_summary = await summarize_pdf_with_ai(filename, text_)
                await session.commit()

    background_tasks.add_task(_summarize, upload.id, file.filename, text)

    return {
        "id": upload.id,
        "filename": file.filename,
        "doc_category": doc_category,
        "page_count": page_count,
        "chars_extracted": len(text),
        "phases_detected": [p.value for p in phases[:5]],
        "params_detected": params,
        "message": "PDF загружен. Краткое содержание будет готово через несколько секунд.",
    }


@router.get("/projects/{project_id}/pdfs", summary="Список загруженных PDF проекта")
async def list_project_pdfs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_project(db, project_id)
    result = await db.execute(
        select(ProjectPdfUpload).where(ProjectPdfUpload.project_id == project_id)
    )
    uploads = result.scalars().all()
    return [
        {
            "id": u.id,
            "filename": u.filename,
            "doc_category": u.doc_category,
            "page_count": u.page_count,
            "chars_extracted": len(u.extracted_text or ""),
            "text_summary": u.text_summary,
            "phases_detected": u.construction_phases_mentioned or [],
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
        }
        for u in uploads
    ]


@router.delete("/projects/{project_id}/pdfs/{upload_id}", summary="Удалить PDF")
async def delete_project_pdf(
    project_id: str,
    upload_id: str,
    db: AsyncSession = Depends(get_db),
):
    u = await db.get(ProjectPdfUpload, upload_id)
    if not u or u.project_id != project_id:
        raise HTTPException(404, "Файл не найден")
    if os.path.exists(u.file_path):
        os.remove(u.file_path)
    await db.delete(u)
    await db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
#  ФАЗЫ СТРОИТЕЛЬСТВА
# ════════════════════════════════════════════════════════════════════════════

@router.get("/phases", summary="Список фаз строительства МГ")
async def get_phases():
    """Полный список фаз: геодезическая разбивка → сдача в эксплуатацию."""
    return [
        {
            "value": phase.value,
            "name_ru": PHASE_NAMES_RU[phase],
            "normatives": PHASE_NORMATIVES.get(phase, []),
            "typical_machinery": PHASE_TYPICAL_MACHINERY.get(phase, []),
        }
        for phase in ConstructionPhase
    ]


# ════════════════════════════════════════════════════════════════════════════
#  СМЕННЫЕ РАПОРТЫ — CRUD
# ════════════════════════════════════════════════════════════════════════════

class ShiftReportCreate(BaseModel):
    project_id: str
    shift_date: datetime
    shift_number: str = "day"                # "day" | "night"
    construction_phase: str                  # ConstructionPhase.value
    shift_foreman: Optional[str] = None
    chainage_start: Optional[str] = None
    chainage_end: Optional[str] = None
    length_done_m: float = 0.0
    weather_morning: Optional[str] = None
    weather_afternoon: Optional[str] = None

    # Опциональные — если не переданы, генерируются через AI
    works_done: Optional[list] = None
    workers_on_site: Optional[dict] = None
    machinery_on_site: Optional[list] = None
    materials_received: Optional[list] = None
    quality_checks: Optional[list] = None
    downtime_hours: float = 0.0
    downtime_reason: Optional[str] = None
    safety_incidents: Optional[str] = None
    documents_issued: Optional[list] = None
    next_shift_plan: Optional[str] = None

    # Флаги
    use_ai: bool = True   # Использовать Claude для заполнения незаполненных полей


class ShiftReportUpdate(BaseModel):
    shift_foreman: Optional[str] = None
    chainage_start: Optional[str] = None
    chainage_end: Optional[str] = None
    length_done_m: Optional[float] = None
    weather_morning: Optional[str] = None
    weather_afternoon: Optional[str] = None
    works_done: Optional[list] = None
    workers_on_site: Optional[dict] = None
    machinery_on_site: Optional[list] = None
    materials_received: Optional[list] = None
    quality_checks: Optional[list] = None
    downtime_hours: Optional[float] = None
    downtime_reason: Optional[str] = None
    safety_incidents: Optional[str] = None
    documents_issued: Optional[list] = None
    next_shift_plan: Optional[str] = None
    is_finalized: Optional[bool] = None
    signed_by: Optional[str] = None


@router.post("/", summary="Создать сменный рапорт")
async def create_shift_report(
    payload: ShiftReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создаёт сменный рапорт.

    - Если `use_ai=true` и не все поля заполнены — Claude заполняет их,
      используя текст загруженных PDF этого проекта.
    - Если `use_ai=false` — сохраняет переданные данные как есть.
    """
    proj = await _get_project(db, payload.project_id)

    try:
        phase = ConstructionPhase(payload.construction_phase)
    except ValueError:
        raise HTTPException(400, f"Неверная фаза: {payload.construction_phase}")

    try:
        shift_num = ShiftNumber(payload.shift_number)
    except ValueError:
        shift_num = ShiftNumber.DAY

    # AI-генерация незаполненных полей
    ai_data: dict = {}
    ai_context: str = ""
    needs_ai = payload.use_ai and (
        payload.works_done is None or payload.workers_on_site is None
    )

    if needs_ai:
        ai_context = await get_pdf_context_for_phase(db, payload.project_id, phase)
        ai_data = await generate_shift_report_with_ai(
            project=_project_dict(proj),
            phase=phase,
            shift_date=payload.shift_date,
            shift_number=shift_num,
            chainage_start=payload.chainage_start or "—",
            chainage_end=payload.chainage_end or "—",
            pdf_context=ai_context,
        )

    def _pick(field: str, default):
        """Вернуть значение из payload, иначе из AI, иначе default."""
        val = getattr(payload, field, None)
        if val is not None:
            return val
        return ai_data.get(field, default)

    report = ShiftReport(
        project_id=payload.project_id,
        shift_date=payload.shift_date,
        shift_number=shift_num,
        shift_foreman=payload.shift_foreman,
        construction_phase=phase,
        chainage_start=payload.chainage_start,
        chainage_end=payload.chainage_end,
        length_done_m=payload.length_done_m,
        weather_morning=payload.weather_morning,
        weather_afternoon=payload.weather_afternoon,
        works_done=_pick("works_done", []),
        workers_on_site=_pick("workers_on_site", {}),
        machinery_on_site=_pick("machinery_on_site", []),
        materials_received=_pick("materials_received", []),
        quality_checks=_pick("quality_checks", []),
        downtime_hours=_pick("downtime_hours", 0.0),
        downtime_reason=_pick("downtime_reason", ""),
        safety_incidents=payload.safety_incidents,
        documents_issued=_pick("documents_issued", []),
        next_shift_plan=_pick("next_shift_plan", ""),
        ai_generated=needs_ai,
        ai_prompt_context=ai_context[:2000] if ai_context else None,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return _report_to_dict(report)


@router.get("/projects/{project_id}/", summary="Рапорты проекта")
async def list_shift_reports(
    project_id: str,
    phase: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(db, project_id)
    q = select(ShiftReport).where(ShiftReport.project_id == project_id)
    if phase:
        try:
            q = q.where(ShiftReport.construction_phase == ConstructionPhase(phase))
        except ValueError:
            pass
    q = q.order_by(ShiftReport.shift_date.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    reports = result.scalars().all()
    return [_report_to_dict(r) for r in reports]


@router.get("/{report_id}", summary="Получить рапорт")
async def get_shift_report(report_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.get(ShiftReport, report_id)
    if not r:
        raise HTTPException(404, "Рапорт не найден")
    return _report_to_dict(r)


@router.patch("/{report_id}", summary="Обновить рапорт")
async def update_shift_report(
    report_id: str,
    payload: ShiftReportUpdate,
    db: AsyncSession = Depends(get_db),
):
    r = await db.get(ShiftReport, report_id)
    if not r:
        raise HTTPException(404, "Рапорт не найден")
    if r.is_finalized:
        raise HTTPException(400, "Рапорт финализирован и не может быть изменён")

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "is_finalized" and value:
            r.is_finalized = True
            r.signed_at = datetime.utcnow()
        else:
            setattr(r, field, value)

    r.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(r)
    return _report_to_dict(r)


@router.delete("/{report_id}", summary="Удалить рапорт")
async def delete_shift_report(report_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.get(ShiftReport, report_id)
    if not r:
        raise HTTPException(404, "Рапорт не найден")
    await db.delete(r)
    await db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
#  СКАЧАТЬ РАПОРТ КАК PDF
# ════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════
#  ФИНАЛИЗАЦИЯ РАПОРТА → АВТО-ГЕНЕРАЦИЯ ИТД
# ════════════════════════════════════════════════════════════════════════════

@router.post("/{report_id}/finalize", summary="Финализировать рапорт и сгенерировать ИТД")
async def finalize_shift_report(
    report_id: str,
    signed_by: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Финализирует рапорт и автоматически создаёт ИТД-документы:
    - Запись в ОЖР (всегда)
    - АОСР — если фаза содержит скрытые работы (траншея, сварка, изоляция и т.д.)
    - Акт гидроиспытаний — если фаза HYDRAULIC_TEST
    Возвращает список сгенерированных документов.
    """
    from app.models.document import Document as DocModel, DocumentType, DocumentStatus
    from app.models.shift_report import PHASE_TYPICAL_AOSR
    from app.services.document_generator import document_generator

    r = await db.get(ShiftReport, report_id)
    if not r:
        raise HTTPException(404, "Рапорт не найден")
    if r.is_finalized:
        raise HTTPException(400, "Рапорт уже финализирован")

    proj = await db.get(Project, r.project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")

    project_dict = _project_dict(proj)
    report_dict = _report_to_dict(r)
    phase = r.construction_phase
    shift_date_str = r.shift_date.strftime("%d.%m.%Y") if r.shift_date else "—"

    generated_docs = []

    # ── 1. Запись в ОЖР ──────────────────────────────────────────────────────
    works_list = r.works_done or []
    ojr_entries = [
        {
            "date": shift_date_str,
            "phase": PHASE_NAMES_RU.get(phase, phase.value if phase else "—"),
            "chainage": f"{r.chainage_start or '—'} — {r.chainage_end or '—'}",
            "work_type": w.get("work_type", ""),
            "unit": w.get("unit", ""),
            "quantity": w.get("quantity", ""),
            "foreman": r.shift_foreman or "—",
        }
        for w in works_list
    ] or [{
        "date": shift_date_str,
        "phase": PHASE_NAMES_RU.get(phase, "—"),
        "chainage": f"{r.chainage_start or '—'} — {r.chainage_end or '—'}",
        "work_type": "Производство работ согласно рапорту",
        "unit": "м",
        "quantity": r.length_done_m or 0,
        "foreman": r.shift_foreman or "—",
    }]

    ojr_path = document_generator.generate_ojr(project_dict, ojr_entries)
    ojr_doc = DocModel(
        project_id=proj.id,
        document_type=DocumentType.OJR,
        title=f"ОЖР — {shift_date_str} ({PHASE_NAMES_RU.get(phase, '')})",
        file_path=ojr_path,
        file_format="docx",
        auto_generated=True,
        content_json={"shift_report_id": report_id, "entries": ojr_entries},
        normative_refs=["СП РК 1.04.02-2019"],
        status=DocumentStatus.DRAFT,
    )
    db.add(ojr_doc)
    await db.flush()
    await db.refresh(ojr_doc)
    generated_docs.append({"type": "ojr", "id": ojr_doc.id, "title": ojr_doc.title})

    # ── 2. АОСР — только если фаза содержит скрытые работы ──────────────────
    if phase in PHASE_TYPICAL_AOSR:
        typical_works = PHASE_TYPICAL_AOSR[phase]
        work_name = typical_works[0] if typical_works else PHASE_NAMES_RU.get(phase, "")
        normatives = PHASE_NORMATIVES.get(phase, ["СП РК 2.04-103-2013*"])

        aosr_data = {
            "work_name": work_name,
            "chainage": f"{r.chainage_start or '—'} — {r.chainage_end or '—'}",
            "work_date": shift_date_str,
            "materials": [
                m.get("name", "—")
                for m in (r.materials_received or [])
            ] or ["Согласно проекту"],
            "normatives": normatives,
            "foreman": r.shift_foreman or "—",
            "author_supervisor": project_dict.get("technical_supervisor", "—"),
            "act_number": f"АОСР-{shift_date_str.replace('.', '')}-{phase.value[:4].upper()}",
            "next_works": r.next_shift_plan or "Согласно ПОС/ППР",
        }
        aosr_path = document_generator.generate_aosr(project_dict, aosr_data)
        aosr_doc = DocModel(
            project_id=proj.id,
            document_type=DocumentType.AOSR,
            document_number=aosr_data["act_number"],
            title=f"АОСР — {work_name} — {shift_date_str}",
            file_path=aosr_path,
            file_format="docx",
            auto_generated=True,
            content_json={"shift_report_id": report_id, **aosr_data},
            normative_refs=normatives,
            status=DocumentStatus.DRAFT,
        )
        db.add(aosr_doc)
        await db.flush()
        await db.refresh(aosr_doc)
        generated_docs.append({"type": "aosr", "id": aosr_doc.id, "title": aosr_doc.title})

    # ── 3. Акт гидроиспытаний ────────────────────────────────────────────────
    if phase == ConstructionPhase.HYDRAULIC_TEST:
        hydraulic_data = {
            "section_chainage": f"{r.chainage_start or '0+00'} — {r.chainage_end or '—'}",
            "length_m": r.length_done_m or 0.0,
            "wall_thickness_mm": 14.0,  # типовое значение — в реальности из ПД
            "steel_grade": "К60",
            "test_pressure_mpa": (proj.working_pressure_mpa or 5.4) * 1.5,
            "tightness_pressure_mpa": proj.working_pressure_mpa or 5.4,
            "test_date": shift_date_str,
            "duration_hours": 24,
            "result": "УДОВЛЕТВОРИТЕЛЬНО",
        }
        hyd_path = document_generator.generate_hydraulic_test_act(project_dict, hydraulic_data)
        hyd_doc = DocModel(
            project_id=proj.id,
            document_type=DocumentType.HYDRAULIC_TEST,
            title=f"Акт гидроиспытаний — ПК {r.chainage_start or '—'} — {shift_date_str}",
            file_path=hyd_path,
            file_format="docx",
            auto_generated=True,
            content_json={"shift_report_id": report_id, **hydraulic_data},
            normative_refs=["СП РК 2.04-103-2013* п.10", "ВСН 012-88"],
            status=DocumentStatus.DRAFT,
        )
        db.add(hyd_doc)
        await db.flush()
        await db.refresh(hyd_doc)
        generated_docs.append({"type": "hydraulic_test", "id": hyd_doc.id, "title": hyd_doc.title})

    # ── Финализация рапорта ───────────────────────────────────────────────────
    r.is_finalized = True
    r.signed_at = datetime.utcnow()
    if signed_by:
        r.signed_by = signed_by
    r.documents_issued = [
        {"type": d["type"], "doc_id": d["id"], "title": d["title"]}
        for d in generated_docs
    ]

    await db.commit()

    return {
        "report_id": report_id,
        "finalized": True,
        "signed_at": r.signed_at.isoformat(),
        "generated_documents": generated_docs,
        "message": f"Рапорт финализирован. Сгенерировано {len(generated_docs)} документ(ов) ИТД.",
    }


@router.get("/{report_id}/download", summary="Скачать рапорт в PDF")
async def download_shift_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Скачать сменный рапорт как PDF-файл."""
    from app.services.pdf_generator import generate_shift_report_pdf

    r = await db.get(ShiftReport, report_id)
    if not r:
        raise HTTPException(404, "Рапорт не найден")
    proj = await db.get(Project, r.project_id)

    report_dict = _report_to_dict(r)
    project_dict = _project_dict(proj) if proj else {}

    pdf_bytes = generate_shift_report_pdf(report_dict, project_dict)

    shift_date_str = r.shift_date.strftime("%Y%m%d") if r.shift_date else "date"
    filename = f"Рапорт_{proj.code if proj else 'PROJ'}_{shift_date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
