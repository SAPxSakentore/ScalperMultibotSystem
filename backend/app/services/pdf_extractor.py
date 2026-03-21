"""
Извлечение текста из PDF-файлов проекта (ПОС, ППР, ПД, НТД).
Использует pdfplumber. Без внешних API — только локальная обработка.
"""
import io
import os
import re
from typing import List, Optional

import pdfplumber

from app.models.shift_report import ConstructionPhase


# ── Ключевые слова для определения фаз в тексте PDF ────────────────────────
_PHASE_KEYWORDS: dict[ConstructionPhase, list[str]] = {
    ConstructionPhase.GEODESY_SURVEY:     ["геодез", "разбивк", "пикетаж", "нивелировани", "теодолит"],
    ConstructionPhase.CLEARING:           ["расчистк", "крп", "кустарник", "лес", "деревья"],
    ConstructionPhase.TOPSOIL_REMOVAL:    ["растительн", "гумус", "снятие грунт", "плодородн"],
    ConstructionPhase.TRENCH_EXCAVATION:  ["траншея", "экскавац", "разработк", "копк", "экскаватор"],
    ConstructionPhase.TRENCH_PREPARATION: ["постель", "подготовк основани", "мягкий грунт"],
    ConstructionPhase.PIPE_WELDING:       ["сварк", "стык", "сварной", "центратор", "клеймо", "сварщик"],
    ConstructionPhase.PIPE_INSULATION:    ["изоляц", "антикоррозий", "покрыти", "праймер", "пэ"],
    ConstructionPhase.PIPE_LAYING:        ["укладк", "трубоукладчик", "опускан"],
    ConstructionPhase.TRANSITIONS:        ["переход", "гнб", "наклонно-направленн", "дюкер", "ннб"],
    ConstructionPhase.TRENCH_BACKFILL:    ["засыпк", "уплотнени", "обратн", "подсыпк"],
    ConstructionPhase.BALLASTING:         ["балластиров", "утяжелител", "анкер"],
    ConstructionPhase.VALVE_INSTALLATION: ["арматур", "кран", "задвижк", "кип", "линейн"],
    ConstructionPhase.ECP_INSTALLATION:   ["эхз", "электрохим", "катодн", "протектор", "кик"],
    ConstructionPhase.HYDRAULIC_TEST:     ["гидравлическ", "испытани", "опрессовк", "давлени", "манометр"],
    ConstructionPhase.PURGE_DRY:          ["продувк", "осушк", "компрессор", "свеча"],
    ConstructionPhase.TIGHTNESS_TEST:     ["герметичн", "пневматическ", "течеискател"],
    ConstructionPhase.EXECUTIVE_SURVEY:   ["исполнительн", "съёмк", "съемк", "план-схем"],
    ConstructionPhase.RECULTIVATION:      ["рекультивац", "восстановлени", "озеленени", "посев"],
    ConstructionPhase.GAS_START:          ["пуск газ", "заполнени", "комплексн испыт", "розжиг"],
    ConstructionPhase.COMMISSIONING:      ["сдача", "эксплуатац", "приёмочн", "кс-14", "кс14", "акт ввод"],
}


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """
    Извлечь весь текст и количество страниц из PDF.
    Возвращает (full_text, page_count).
    """
    pages_text: list[str] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if text:
                    pages_text.append(text)
            page_count = len(pdf.pages)
    except Exception as exc:
        raise RuntimeError(f"Не удалось прочитать PDF {file_path}: {exc}") from exc

    full_text = "\n\n".join(pages_text)
    return full_text, page_count


def extract_text_from_bytes(pdf_bytes: bytes) -> tuple[str, int]:
    """То же, но из байт (UploadFile)."""
    buf = io.BytesIO(pdf_bytes)
    pages_text: list[str] = []
    try:
        with pdfplumber.open(buf) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if text:
                    pages_text.append(text)
            page_count = len(pdf.pages)
    except Exception as exc:
        raise RuntimeError(f"Не удалось прочитать PDF: {exc}") from exc

    full_text = "\n\n".join(pages_text)
    return full_text, page_count


def detect_phases_in_text(text: str) -> list[ConstructionPhase]:
    """
    Определить, какие фазы строительства упоминаются в тексте PDF.
    Возвращает список фаз в порядке их встречаемости.
    """
    text_lower = text.lower()
    found: dict[ConstructionPhase, int] = {}
    for phase, keywords in _PHASE_KEYWORDS.items():
        count = sum(len(re.findall(kw, text_lower)) for kw in keywords)
        if count > 0:
            found[phase] = count

    # Сортируем по убыванию упоминаний
    return [ph for ph, _ in sorted(found.items(), key=lambda x: -x[1])]


def get_relevant_context(
    text: str,
    phase: ConstructionPhase,
    max_chars: int = 4000,
) -> str:
    """
    Извлечь из текста PDF самые релевантные параграфы для заданной фазы.
    Используется для формирования контекста AI-генерации рапорта.
    """
    keywords = _PHASE_KEYWORDS.get(phase, [])
    if not keywords:
        return text[:max_chars]

    paragraphs = re.split(r"\n{2,}", text)
    scored: list[tuple[int, str]] = []

    for para in paragraphs:
        para_lower = para.lower()
        score = sum(
            len(re.findall(kw, para_lower)) * (5 if i == 0 else 1)
            for i, kw in enumerate(keywords)
        )
        if score > 0:
            scored.append((score, para.strip()))

    scored.sort(key=lambda x: -x[0])

    result_parts: list[str] = []
    total = 0
    for _, para in scored:
        if total + len(para) > max_chars:
            break
        result_parts.append(para)
        total += len(para)

    return "\n\n".join(result_parts) if result_parts else text[:max_chars]


def extract_project_parameters(text: str) -> dict:
    """
    Попытаться извлечь ключевые параметры проекта из текста PDF
    (шифр, диаметр, давление, длина, участки ПК).
    """
    params: dict = {}

    # Диаметр трубы
    m = re.search(r"DN\s*(\d{3,4})|диаметр[^0-9]*(\d{3,4})\s*мм", text, re.IGNORECASE)
    if m:
        params["diameter_mm"] = int(m.group(1) or m.group(2))

    # Рабочее давление
    m = re.search(r"рабоч[^0-9]*?(\d+[.,]\d+)\s*МПа", text, re.IGNORECASE)
    if m:
        params["working_pressure_mpa"] = float(m.group(1).replace(",", "."))

    # Длина
    m = re.search(r"длин[^0-9]*?(\d+[.,]?\d*)\s*км", text, re.IGNORECASE)
    if m:
        params["total_length_km"] = float(m.group(1).replace(",", "."))

    # Марка стали
    m = re.search(r"\b(К\d{2}|17Г1С[А-Я\-]?|Х\d{2}[А-Я]?\d?)\b", text)
    if m:
        params["steel_grade"] = m.group(1)

    # Шифр проекта
    m = re.search(r"шифр[:\s]+([А-ЯA-Z0-9\-/]+)", text, re.IGNORECASE)
    if m:
        params["project_code"] = m.group(1).strip()

    # Пикеты
    pks = re.findall(r"ПК\s*(\d+\+\d+)", text)
    if pks:
        params["chainages_mentioned"] = list(dict.fromkeys(pks))[:20]

    return params
