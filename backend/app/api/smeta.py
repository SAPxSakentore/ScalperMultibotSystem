"""
API для управления сметными позициями проекта и генерации КС-2/КС-3 по накопленным объёмам.

Ключевые endpoint-ы:
  GET  /api/smeta/project/{id}                — список позиций сметы
  POST /api/smeta/                            — создать позицию
  PUT  /api/smeta/{id}                        — обновить позицию
  DELETE /api/smeta/{id}                      — удалить позицию
  POST /api/smeta/project/{id}/import-bulk    — массовый ввод позиций (JSON-список)
  GET  /api/smeta/project/{id}/work-volumes   — агрегация объёмов по рапортам за период
  POST /api/smeta/project/{id}/generate-acts  — сгенерировать КС-2, КС-3 по объёмам
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from collections import defaultdict
import io, zipfile, difflib
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

from app.core.database import get_db
from app.models.smeta import SmetaItem
from app.models.project import Project
from app.models.shift_report import ShiftReport
from app.models.document import Document, DocumentType, DocumentStatus
from app.services.document_generator import document_generator

router = APIRouter(prefix="/api/smeta", tags=["smeta"])

# ─── Excel-генератор КС-2 + КС-3 ─────────────────────────────────────────────

_THIN = Side(style="thin")
_MEDIUM = Side(style="medium")

def _xl_border(thin=True):
    s = _THIN if thin else _MEDIUM
    return Border(left=s, right=s, top=s, bottom=s)

def _xl_fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)

def _xl_cell(ws, row, col, value, bold=False, fill=None, align="left",
             num_fmt=None, border=True, font_size=10):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(bold=bold, size=font_size)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    if fill:
        cell.fill = _xl_fill(fill)
    if num_fmt:
        cell.number_format = num_fmt
    if border:
        cell.border = _xl_border()
    return cell


def _generate_excel_ks(project_dict: Dict, ks2_data: Dict, ks3_data: Dict, period_label: str) -> io.BytesIO:
    """Генерирует XLSX с двумя листами: КС-2 и КС-3."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # удаляем дефолтный лист

    # ── Лист КС-2 ─────────────────────────────────────────────────────────────
    ws2 = wb.create_sheet("КС-2")
    ws2.sheet_view.showGridLines = False

    # Заголовок
    ws2.merge_cells("A1:J1")
    _xl_cell(ws2, 1, 1, "АКТ О ПРИЁМКЕ ВЫПОЛНЕННЫХ РАБОТ (Форма КС-2)",
             bold=True, align="center", fill="1F3864", font_size=12)
    ws2["A1"].font = Font(bold=True, size=12, color="FFFFFF")
    ws2.row_dimensions[1].height = 24

    ws2.merge_cells("A2:J2")
    _xl_cell(ws2, 2, 1, f"Период: {period_label}", align="center", fill="BDD7EE")

    # Реквизиты
    req_rows = [
        ("Заказчик:", project_dict.get("customer_name", "")),
        ("Подрядчик:", project_dict.get("contractor_name", "")),
        ("Объект:", project_dict.get("name", "")),
        ("Шифр:", project_dict.get("code", "")),
        ("№ договора:", ks2_data.get("contract_number", "")),
    ]
    for i, (lbl, val) in enumerate(req_rows, 3):
        ws2.merge_cells(f"A{i}:B{i}")
        _xl_cell(ws2, i, 1, lbl, bold=True, border=False)
        ws2.merge_cells(f"C{i}:J{i}")
        _xl_cell(ws2, i, 3, val, border=False)

    # Шапка таблицы
    HDR = [
        "№", "Код НТД", "Наименование работ и затрат", "Ед.",
        "Объём\nпо смете", "Выполнено\nза период", "Нарастающим\nитогом",
        "Цена за ед.,\nтг.", "Сумма\nза период, тг.", "Сумма\nнарастающая, тг.",
    ]
    HDR_WIDTHS = [5, 12, 40, 6, 12, 14, 14, 14, 16, 16]
    for col, (h, w) in enumerate(zip(HDR, HDR_WIDTHS), 1):
        _xl_cell(ws2, 8, col, h, bold=True, fill="2F5496", align="center")
        ws2.cell(8, col).font = Font(bold=True, color="FFFFFF", size=9)
        ws2.column_dimensions[get_column_letter(col)].width = w
    ws2.row_dimensions[8].height = 36
    ws2.freeze_panes = "A9"

    works = ks2_data.get("works", [])
    current_section = None
    row_no = 9
    total_period = 0.0
    total_cumul = 0.0

    NUM_FMT = '#,##0.00'

    for w in works:
        sec = w.get("section", "")
        if sec and sec != current_section:
            current_section = sec
            ws2.merge_cells(f"A{row_no}:J{row_no}")
            _xl_cell(ws2, row_no, 1, sec, bold=True, fill="D6E4F0", align="center")
            row_no += 1

        qty    = float(w.get("quantity", 0) or 0)
        c_qty  = float(w.get("cumulative_qty", 0) or 0)
        price  = float(w.get("unit_price", 0) or 0)
        amount = float(w.get("amount", qty * price))
        c_amount = float(w.get("cumulative_amount", c_qty * price))
        total_period += amount
        total_cumul  += c_amount

        fill = "FFFFFF" if row_no % 2 == 0 else "F7FBFF"
        _xl_cell(ws2, row_no, 1, w.get("position_no", ""), align="center", fill=fill)
        _xl_cell(ws2, row_no, 2, w.get("normative_code", ""), fill=fill)
        name_cell = _xl_cell(ws2, row_no, 3, w.get("name", ""), fill=fill)
        chainages = w.get("chainages", "")
        if chainages:
            name_cell.value = f"{w.get('name','')} ({chainages})"
        _xl_cell(ws2, row_no, 4, w.get("unit", ""), align="center", fill=fill)
        _xl_cell(ws2, row_no, 5, w.get("planned_qty", 0), align="right", fill=fill, num_fmt='#,##0.##')
        _xl_cell(ws2, row_no, 6, qty,     align="right", fill="E2EFDA", num_fmt=NUM_FMT)
        _xl_cell(ws2, row_no, 7, c_qty,   align="right", fill=fill,     num_fmt='#,##0.##')
        _xl_cell(ws2, row_no, 8, price,   align="right", fill=fill,     num_fmt=NUM_FMT)
        _xl_cell(ws2, row_no, 9, amount,  align="right", fill="E2EFDA", num_fmt=NUM_FMT)
        _xl_cell(ws2, row_no, 10, c_amount, align="right", fill=fill,   num_fmt=NUM_FMT)
        ws2.row_dimensions[row_no].height = 18
        row_no += 1

    # Итого
    ws2.merge_cells(f"A{row_no}:H{row_no}")
    _xl_cell(ws2, row_no, 1, "ИТОГО:", bold=True, fill="1F3864", align="right")
    ws2.cell(row_no, 1).font = Font(bold=True, color="FFFFFF")
    _xl_cell(ws2, row_no, 9, total_period, bold=True, fill="E2EFDA", align="right", num_fmt=NUM_FMT)
    _xl_cell(ws2, row_no, 10, total_cumul, bold=True, fill="BDD7EE", align="right", num_fmt=NUM_FMT)
    ws2.row_dimensions[row_no].height = 20
    row_no += 1

    nds = total_period * 0.12
    ws2.merge_cells(f"A{row_no}:H{row_no}")
    _xl_cell(ws2, row_no, 1, "НДС (12%):", bold=True, fill="FCE4D6", align="right")
    _xl_cell(ws2, row_no, 9, nds, fill="FCE4D6", align="right", num_fmt=NUM_FMT)
    row_no += 1
    ws2.merge_cells(f"A{row_no}:H{row_no}")
    _xl_cell(ws2, row_no, 1, "ИТОГО С НДС:", bold=True, fill="FCE4D6", align="right")
    _xl_cell(ws2, row_no, 9, total_period + nds, bold=True, fill="FCE4D6", align="right", num_fmt=NUM_FMT)

    # Подписи
    row_no += 2
    ws2.merge_cells(f"A{row_no}:E{row_no}")
    ws2.cell(row_no, 1).value = f"Сдал (Подрядчик): {project_dict.get('contractor_name','')}  _______________________  М.П."
    row_no += 1
    ws2.merge_cells(f"A{row_no}:E{row_no}")
    ws2.cell(row_no, 1).value = f"Принял (Заказчик): {project_dict.get('customer_name','')}  _______________________  М.П."

    # ── Лист КС-3 ─────────────────────────────────────────────────────────────
    ws3 = wb.create_sheet("КС-3")
    ws3.sheet_view.showGridLines = False
    ws3.column_dimensions["A"].width = 6
    ws3.column_dimensions["B"].width = 38
    ws3.column_dimensions["C"].width = 20
    ws3.column_dimensions["D"].width = 24
    ws3.column_dimensions["E"].width = 24

    ws3.merge_cells("A1:E1")
    _xl_cell(ws3, 1, 1, "СПРАВКА О СТОИМОСТИ ВЫПОЛНЕННЫХ РАБОТ И ЗАТРАТ (КС-3)",
             bold=True, align="center", fill="1F3864", font_size=12)
    ws3["A1"].font = Font(bold=True, size=12, color="FFFFFF")
    ws3.row_dimensions[1].height = 24

    ws3.merge_cells("A2:E2")
    _xl_cell(ws3, 2, 1, f"Период: {period_label}", align="center", fill="BDD7EE")

    req3 = [
        ("Заказчик:", project_dict.get("customer_name", "")),
        ("Подрядчик:", project_dict.get("contractor_name", "")),
        ("Объект:", project_dict.get("name", "")),
        ("№ договора:", ks2_data.get("contract_number", "")),
    ]
    for i, (lbl, val) in enumerate(req3, 3):
        _xl_cell(ws3, i, 1, lbl, bold=True, border=False)
        ws3.merge_cells(f"B{i}:E{i}")
        _xl_cell(ws3, i, 2, val, border=False)

    hdr3 = ["№", "Наименование затрат", "Сметная стоимость, тг.", "Выполнено с начала, тг.", "За отчётный период, тг."]
    for col, h in enumerate(hdr3, 1):
        _xl_cell(ws3, 7, col, h, bold=True, fill="2F5496", align="center")
        ws3.cell(7, col).font = Font(bold=True, color="FFFFFF", size=9)
    ws3.row_dimensions[7].height = 28

    total_period_ks3  = float(ks3_data.get("total_period", 0))
    total_cumul_ks3   = float(ks3_data.get("total_cumulative", 0))
    total_planned_ks3 = float(ks3_data.get("total_planned", 0))
    nds3      = total_period_ks3 * 0.12
    nds3_cumul = total_cumul_ks3 * 0.12

    data_rows = [
        ("1", "Строительно-монтажные работы", total_planned_ks3, total_cumul_ks3, total_period_ks3),
    ]
    for i, (pos, name, planned, cumul, period) in enumerate(data_rows, 8):
        fill = "F7FBFF"
        _xl_cell(ws3, i, 1, pos, align="center", fill=fill)
        _xl_cell(ws3, i, 2, name, fill=fill)
        _xl_cell(ws3, i, 3, planned, align="right", fill=fill, num_fmt=NUM_FMT)
        _xl_cell(ws3, i, 4, cumul,   align="right", fill=fill, num_fmt=NUM_FMT)
        _xl_cell(ws3, i, 5, period,  align="right", fill="E2EFDA", num_fmt=NUM_FMT)

    r = len(data_rows) + 8
    _xl_cell(ws3, r, 1, "", fill="DDEBF7")
    _xl_cell(ws3, r, 2, "ИТОГО:", bold=True, fill="DDEBF7")
    _xl_cell(ws3, r, 3, total_planned_ks3, bold=True, align="right", fill="DDEBF7", num_fmt=NUM_FMT)
    _xl_cell(ws3, r, 4, total_cumul_ks3,   bold=True, align="right", fill="DDEBF7", num_fmt=NUM_FMT)
    _xl_cell(ws3, r, 5, total_period_ks3,  bold=True, align="right", fill="E2EFDA", num_fmt=NUM_FMT)
    r += 1
    _xl_cell(ws3, r, 2, "НДС (12%):", fill="FCE4D6")
    _xl_cell(ws3, r, 4, nds3_cumul,        align="right", fill="FCE4D6", num_fmt=NUM_FMT)
    _xl_cell(ws3, r, 5, nds3,              align="right", fill="FCE4D6", num_fmt=NUM_FMT)
    r += 1
    _xl_cell(ws3, r, 2, "ИТОГО С НДС:", bold=True, fill="FCE4D6")
    _xl_cell(ws3, r, 4, total_cumul_ks3 + nds3_cumul, bold=True, align="right", fill="FCE4D6", num_fmt=NUM_FMT)
    _xl_cell(ws3, r, 5, total_period_ks3 + nds3,      bold=True, align="right", fill="FCE4D6", num_fmt=NUM_FMT)

    r += 2
    ws3.cell(r, 1).value = f"Сдал (Подрядчик): {project_dict.get('contractor_name','')}  _________________________  М.П."
    r += 1
    ws3.cell(r, 1).value = f"Принял (Заказчик): {project_dict.get('customer_name','')}  _________________________  М.П."

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class SmetaItemCreate(BaseModel):
    project_id: str
    position_no: int = 1
    section: str = ""
    name: str
    work_type_key: str = ""          # матчинг с works_done[].work_type
    unit: str
    unit_price: float
    planned_qty: float
    normative_code: str = ""
    notes: str = ""


class SmetaItemUpdate(BaseModel):
    position_no: Optional[int] = None
    section: Optional[str] = None
    name: Optional[str] = None
    work_type_key: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    planned_qty: Optional[float] = None
    normative_code: Optional[str] = None
    notes: Optional[str] = None


class SmetaItemResponse(BaseModel):
    id: str
    project_id: str
    position_no: int
    section: str
    name: str
    work_type_key: str
    unit: str
    unit_price: float
    planned_qty: float
    planned_amount: float
    normative_code: str
    notes: str

    class Config:
        from_attributes = True


class WorkVolumeRow(BaseModel):
    """Строка агрегации: смета + накопленный факт из рапортов."""
    smeta_id: Optional[str] = None
    position_no: int
    section: str
    name: str
    work_type_key: str
    unit: str
    unit_price: float
    planned_qty: float
    planned_amount: float
    actual_qty: float                  # из рапортов за период
    actual_amount: float               # = actual_qty * unit_price
    cumulative_qty: float              # с начала стройки
    cumulative_amount: float
    completion_pct: float              # actual / planned * 100
    chainage_list: List[str]           # участки, упомянутые в рапортах
    source_reports: int                # кол-во рапортов, из которых собрано

    @classmethod
    def from_smeta(cls, item: SmetaItem, agg: Dict) -> "WorkVolumeRow":
        actual_qty = agg.get("actual_qty", 0.0)
        cumulative_qty = agg.get("cumulative_qty", 0.0)
        planned = item.planned_qty or 1
        return cls(
            smeta_id=item.id,
            position_no=item.position_no,
            section=item.section or "",
            name=item.name,
            work_type_key=item.work_type_key or "",
            unit=item.unit,
            unit_price=item.unit_price,
            planned_qty=item.planned_qty,
            planned_amount=round(item.unit_price * item.planned_qty, 2),
            actual_qty=actual_qty,
            actual_amount=round(item.unit_price * actual_qty, 2),
            cumulative_qty=cumulative_qty,
            cumulative_amount=round(item.unit_price * cumulative_qty, 2),
            completion_pct=round(actual_qty / planned * 100, 1) if planned > 0 else 0,
            chainage_list=agg.get("chainages", []),
            source_reports=agg.get("reports", 0),
        )


class GenerateActsRequest(BaseModel):
    date_from: date
    date_to: date
    period_label: Optional[str] = None        # "Январь 2026" — подставляется в акт
    contract_number: Optional[str] = None
    act_number: Optional[str] = None
    include_zero_rows: bool = False           # включать ли позиции с нулевым объёмом
    output: str = "zip"                       # "zip" | "ks2" | "ks3" | "xlsx"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _project_to_dict(p: Project) -> Dict:
    return {
        "id": p.id, "code": p.code or "", "name": p.name or "",
        "region": p.region or "", "customer_name": p.customer_name or "",
        "contractor_name": p.contractor_name or "",
        "technical_supervisor": p.technical_supervisor or "",
        "diameter_mm": p.diameter_mm, "working_pressure_mpa": p.working_pressure_mpa,
        "total_length_km": p.total_length_km,
    }


FUZZY_THRESHOLD = 0.62  # минимальное сходство для нечёткого матчинга

def _normalize_key(s: str) -> str:
    """Нормализует строку (нижний регистр, без лишних пробелов)."""
    return " ".join(s.lower().split())


def _fuzzy_match(query: str, candidates: List[str], threshold: float = FUZZY_THRESHOLD) -> Optional[str]:
    """
    Возвращает наилучшее совпадение из candidates для query с помощью difflib.
    Если ни одно не превышает threshold — возвращает None.
    """
    if not query or not candidates:
        return None
    matches = difflib.get_close_matches(query, candidates, n=1, cutoff=threshold)
    return matches[0] if matches else None


async def _aggregate_volumes(
    db: AsyncSession,
    project_id: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    cumulative: bool = False,
) -> Dict[str, Dict]:
    """
    Суммирует works_done из финализированных рапортов проекта за период.
    Возвращает словарь { normalized_work_type: {actual_qty, chainages, reports} }.
    """
    stmt = (
        select(ShiftReport)
        .where(ShiftReport.project_id == project_id)
        .where(ShiftReport.is_finalized == True)
    )
    if not cumulative:
        if date_from:
            stmt = stmt.where(ShiftReport.shift_date >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            stmt = stmt.where(ShiftReport.shift_date <= datetime.combine(date_to, datetime.max.time()))

    result = await db.execute(stmt)
    reports = result.scalars().all()

    agg: Dict[str, Dict] = defaultdict(lambda: {"actual_qty": 0.0, "chainages": set(), "reports": 0})
    for rep in reports:
        works = rep.works_done or []
        chainage = f"{rep.chainage_start or ''} — {rep.chainage_end or ''}".strip(" —")
        if not works:
            continue
        seen_in_report: set = set()
        for w in works:
            wtype = _normalize_key(w.get("work_type", ""))
            if not wtype:
                continue
            qty = float(w.get("quantity", 0) or 0)
            agg[wtype]["actual_qty"] += qty
            if chainage:
                agg[wtype]["chainages"].add(chainage)
            if wtype not in seen_in_report:
                agg[wtype]["reports"] += 1
                seen_in_report.add(wtype)

    # конвертируем set в list
    for k in agg:
        agg[k]["chainages"] = sorted(agg[k]["chainages"])
    return dict(agg)


# ─── Routes: CRUD ─────────────────────────────────────────────────────────────

@router.get("/project/{project_id}", response_model=List[SmetaItemResponse])
async def list_smeta(project_id: str, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")
    result = await db.execute(
        select(SmetaItem)
        .where(SmetaItem.project_id == project_id)
        .where(SmetaItem.is_active == True)
        .order_by(SmetaItem.position_no)
    )
    items = result.scalars().all()
    return [SmetaItemResponse(
        id=i.id, project_id=i.project_id, position_no=i.position_no,
        section=i.section or "", name=i.name, work_type_key=i.work_type_key or "",
        unit=i.unit, unit_price=i.unit_price, planned_qty=i.planned_qty,
        planned_amount=i.planned_amount, normative_code=i.normative_code or "",
        notes=i.notes or "",
    ) for i in items]


@router.post("/", response_model=SmetaItemResponse, status_code=201)
async def create_smeta_item(body: SmetaItemCreate, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, body.project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")
    item = SmetaItem(**body.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return SmetaItemResponse(
        id=item.id, project_id=item.project_id, position_no=item.position_no,
        section=item.section or "", name=item.name, work_type_key=item.work_type_key or "",
        unit=item.unit, unit_price=item.unit_price, planned_qty=item.planned_qty,
        planned_amount=item.planned_amount, normative_code=item.normative_code or "",
        notes=item.notes or "",
    )


@router.put("/{item_id}", response_model=SmetaItemResponse)
async def update_smeta_item(item_id: str, body: SmetaItemUpdate, db: AsyncSession = Depends(get_db)):
    item = await db.get(SmetaItem, item_id)
    if not item:
        raise HTTPException(404, "Позиция сметы не найдена")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.flush()
    await db.refresh(item)
    return SmetaItemResponse(
        id=item.id, project_id=item.project_id, position_no=item.position_no,
        section=item.section or "", name=item.name, work_type_key=item.work_type_key or "",
        unit=item.unit, unit_price=item.unit_price, planned_qty=item.planned_qty,
        planned_amount=item.planned_amount, normative_code=item.normative_code or "",
        notes=item.notes or "",
    )


@router.delete("/{item_id}", status_code=204)
async def delete_smeta_item(item_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(SmetaItem, item_id)
    if not item:
        raise HTTPException(404, "Позиция сметы не найдена")
    item.is_active = False


@router.post("/project/{project_id}/import-bulk", response_model=List[SmetaItemResponse], status_code=201)
async def import_smeta_bulk(
    project_id: str,
    items: List[SmetaItemCreate],
    db: AsyncSession = Depends(get_db),
):
    """
    Массовый импорт позиций сметы (заменяет существующие при replace=true).
    Пример JSON: [ {"position_no":1, "name":"Земляные работы", "unit":"м³", "unit_price":5000, "planned_qty":1200, ...}, ... ]
    """
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")

    created = []
    for body in items:
        body.project_id = project_id
        obj = SmetaItem(**body.model_dump())
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        created.append(SmetaItemResponse(
            id=obj.id, project_id=obj.project_id, position_no=obj.position_no,
            section=obj.section or "", name=obj.name, work_type_key=obj.work_type_key or "",
            unit=obj.unit, unit_price=obj.unit_price, planned_qty=obj.planned_qty,
            planned_amount=obj.planned_amount, normative_code=obj.normative_code or "",
            notes=obj.notes or "",
        ))
    return created


# ─── Route: Агрегация объёмов за период ─────────────────────────────────────

@router.get("/project/{project_id}/work-volumes", response_model=List[WorkVolumeRow])
async def get_work_volumes(
    project_id: str,
    date_from: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    date_to:   date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список позиций сметы с накопленными объёмами из рапортов за период.

    Сопоставление рапортных записей (works_done[].work_type) с позициями сметы:
    - точное совпадение по work_type_key (нижний регистр)
    - если position_no = 0 — добавляется как внесметная строка
    """
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")

    # Позиции сметы
    smeta_result = await db.execute(
        select(SmetaItem)
        .where(SmetaItem.project_id == project_id)
        .where(SmetaItem.is_active == True)
        .order_by(SmetaItem.position_no)
    )
    smeta_items = smeta_result.scalars().all()

    # Агрегация за период
    period_agg = await _aggregate_volumes(db, project_id, date_from, date_to, cumulative=False)
    # Накопительная агрегация с начала (до конца периода)
    cumul_agg  = await _aggregate_volumes(db, project_id, None, date_to, cumulative=True)

    # Строим словари ключей сметы для матчинга
    smeta_keys = {_normalize_key(i.work_type_key or i.name): i for i in smeta_items}
    report_keys = list(period_agg.keys())

    rows: List[WorkVolumeRow] = []
    matched_report_keys: set = set()

    for item in smeta_items:
        smeta_key = _normalize_key(item.work_type_key or item.name)

        # 1. Точное совпадение
        p_data = period_agg.get(smeta_key, {})
        c_data = cumul_agg.get(smeta_key, {})
        matched_rkey = smeta_key if smeta_key in period_agg else None

        # 2. Нечёткое совпадение (если точного нет)
        if not matched_rkey:
            fuzzy_rkey = _fuzzy_match(smeta_key, report_keys)
            if fuzzy_rkey:
                p_data = period_agg.get(fuzzy_rkey, {})
                c_data = cumul_agg.get(fuzzy_rkey, {})
                matched_rkey = fuzzy_rkey

        if matched_rkey:
            matched_report_keys.add(matched_rkey)

        agg = {
            "actual_qty": p_data.get("actual_qty", 0.0),
            "cumulative_qty": c_data.get("actual_qty", 0.0),
            "chainages": p_data.get("chainages", []),
            "reports": p_data.get("reports", 0),
        }
        rows.append(WorkVolumeRow.from_smeta(item, agg))

    # Внесметные строки — есть в рапортах, но нет в смете (даже нечётко)
    unmatched_rkeys = [k for k in period_agg if k not in matched_report_keys]
    pos = len(smeta_items) + 1
    for wkey in unmatched_rkeys:
        data = period_agg[wkey]
        c_data = cumul_agg.get(wkey, {})
        rows.append(WorkVolumeRow(
            smeta_id=None,
            position_no=pos,
            section="Внесметные работы",
            name=wkey,
            work_type_key=wkey,
            unit="—",
            unit_price=0.0,
            planned_qty=0.0,
            planned_amount=0.0,
            actual_qty=data.get("actual_qty", 0.0),
            actual_amount=0.0,
            cumulative_qty=c_data.get("actual_qty", 0.0),
            cumulative_amount=0.0,
            completion_pct=0.0,
            chainage_list=data.get("chainages", []),
            source_reports=data.get("reports", 0),
        ))
        pos += 1

    return rows


# ─── Route: Генерация КС-2, КС-3 за период ──────────────────────────────────

@router.post("/project/{project_id}/generate-acts")
async def generate_acts_for_period(
    project_id: str,
    body: GenerateActsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Суммирует объёмы из рапортов за период, сопоставляет с расценками сметы,
    генерирует КС-2 + КС-3 с реальными объёмами и возвращает ZIP-архив
    (или один из документов если output != 'zip').
    """
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(404, "Проект не найден")

    project_dict = _project_to_dict(proj)

    # Позиции сметы
    smeta_result = await db.execute(
        select(SmetaItem)
        .where(SmetaItem.project_id == project_id)
        .where(SmetaItem.is_active == True)
        .order_by(SmetaItem.position_no)
    )
    smeta_items = smeta_result.scalars().all()

    # Агрегация за период и накопительно
    period_agg = await _aggregate_volumes(db, project_id, body.date_from, body.date_to, cumulative=False)
    cumul_agg  = await _aggregate_volumes(db, project_id, None, body.date_to, cumulative=True)

    # Формируем строки для КС-2
    period_label = body.period_label or f"{body.date_from.strftime('%d.%m.%Y')} — {body.date_to.strftime('%d.%m.%Y')}"

    report_keys_list = list(period_agg.keys())
    smeta_matched_keys: set = set()

    ks2_works = []
    total_period = 0.0
    total_cumul  = 0.0
    total_planned = 0.0

    for item in smeta_items:
        key = _normalize_key(item.work_type_key or item.name)
        # Точное совпадение
        p_data = period_agg.get(key, {})
        c_data = cumul_agg.get(key, {})
        matched_k = key if key in period_agg else None
        # Нечёткое
        if not matched_k:
            fuzzy_k = _fuzzy_match(key, report_keys_list)
            if fuzzy_k:
                p_data = period_agg.get(fuzzy_k, {})
                c_data = cumul_agg.get(fuzzy_k, {})
                matched_k = fuzzy_k
        if matched_k:
            smeta_matched_keys.add(matched_k)

        p_qty    = p_data.get("actual_qty", 0.0)
        c_qty    = c_data.get("actual_qty", 0.0)
        chainages = p_data.get("chainages", [])

        if not body.include_zero_rows and p_qty == 0:
            continue

        p_amt = round(item.unit_price * p_qty, 2)
        c_amt = round(item.unit_price * c_qty, 2)
        total_period  += p_amt
        total_cumul   += c_amt
        total_planned += item.planned_amount

        ks2_works.append({
            "position_no":    item.position_no,
            "normative_code": item.normative_code or "",
            "section":        item.section or "",
            "name":           item.name,
            "unit":           item.unit,
            "planned_qty":    item.planned_qty,
            "quantity":       p_qty,       # объём за период
            "cumulative_qty": c_qty,       # объём нарастающим
            "unit_price":     item.unit_price,
            "amount":         p_amt,
            "cumulative_amount": c_amt,
            "chainages":      ", ".join(chainages[:3]),
        })

    # Внесметные строки (не покрыты сметой даже нечётко)
    for wkey, data in period_agg.items():
        if wkey in smeta_matched_keys:
            continue
        qty = data.get("actual_qty", 0.0)
        ks2_works.append({
            "position_no": 999, "normative_code": "", "section": "Внесметные работы",
            "name": wkey, "unit": "—", "planned_qty": 0, "quantity": qty,
            "cumulative_qty": cumul_agg.get(wkey, {}).get("actual_qty", 0.0),
            "unit_price": 0, "amount": 0, "cumulative_amount": 0,
            "chainages": ", ".join(data.get("chainages", [])[:3]),
        })

    ks2_data = {
        "period":          period_label,
        "contract_number": body.contract_number or "_______________",
        "act_number":      body.act_number or f"КС2-{body.date_to.strftime('%Y%m')}",
        "works":           ks2_works,
        "total_period":    total_period,
        "total_cumulative": total_cumul,
        "total_planned":   total_planned,
    }
    ks3_data = {
        "period":          period_label,
        "contract_number": body.contract_number or "_______________",
        "total_period":    total_period,
        "total_cumulative": total_cumul,
        "total_planned":   total_planned,
        "act_ref":         ks2_data["act_number"],
    }

    # Генерация документов
    ks2_path = document_generator.generate_ks2_full(project_dict, ks2_data)
    ks3_path = document_generator.generate_ks3_from_ks2(project_dict, ks3_data)

    # Сохраняем в БД
    for dtype, title, path, refs in [
        (DocumentType.KS2, f"КС-2 ({period_label})", ks2_path, ["Приказ МФ РК"]),
        (DocumentType.KS3, f"КС-3 ({period_label})", ks3_path, ["Приказ МФ РК"]),
    ]:
        doc = Document(
            project_id=project_id,
            document_type=dtype,
            title=title,
            file_path=path,
            file_format="docx",
            auto_generated=True,
            content_json={
                "period": period_label,
                "date_from": str(body.date_from),
                "date_to": str(body.date_to),
                "total_period": total_period,
            },
            normative_refs=refs,
            status=DocumentStatus.DRAFT,
        )
        db.add(doc)
    await db.commit()

    if body.output == "ks2":
        with open(ks2_path, "rb") as f:
            content = f.read()
        fname = f"KS2_{proj.code}_{body.date_to.strftime('%Y%m')}.docx"
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    if body.output == "ks3":
        with open(ks3_path, "rb") as f:
            content = f.read()
        fname = f"KS3_{proj.code}_{body.date_to.strftime('%Y%m')}.docx"
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    if body.output == "xlsx":
        xls_buf = _generate_excel_ks(project_dict, ks2_data, ks3_data, period_label)
        fname = f"Acts_{proj.code}_{body.date_to.strftime('%Y%m')}.xlsx"
        return StreamingResponse(
            xls_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    # ZIP (DOCX + DOCX)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        with open(ks2_path, "rb") as f:
            zf.writestr(f"КС-2_{period_label}.docx", f.read())
        with open(ks3_path, "rb") as f:
            zf.writestr(f"КС-3_{period_label}.docx", f.read())
        # добавляем xlsx в ZIP тоже
        xls_buf = _generate_excel_ks(project_dict, ks2_data, ks3_data, period_label)
        zf.writestr(f"КС-2_КС-3_{period_label}.xlsx", xls_buf.getvalue())
    buf.seek(0)
    fname = f"Acts_{proj.code}_{body.date_to.strftime('%Y%m')}.zip"
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
