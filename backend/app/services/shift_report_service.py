"""
Сервис генерации и управления сменными рапортами.
Использует контекст из загруженных PDF проекта + Claude AI.
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.shift_report import (
    ConstructionPhase,
    PHASE_NAMES_RU,
    PHASE_NORMATIVES,
    PHASE_TYPICAL_AOSR,
    PHASE_TYPICAL_MACHINERY,
    ProjectPdfUpload,
    ShiftReport,
    ShiftNumber,
)
from app.services.pdf_extractor import get_relevant_context


# ── Системный промпт для AI-генерации ────────────────────────────────────────

_SYSTEM_PROMPT = """
Ты — опытный прораб строительства магистральных газопроводов Казахстана.
Ты знаешь требования ВСН 012-88, СП РК 2.04-103-2013*, СП РК 1.04.02-2019,
СНиП РК 3.01.01-2008*, нормы НАКС РК и правила ведения ИТД.

Твоя задача — помочь заполнить сменный производственный рапорт.
Отвечай ТОЛЬКО валидным JSON без markdown-обёртки, без пояснений.
"""

_FILL_REPORT_PROMPT_TEMPLATE = """
Данные проекта:
{project_json}

Текущая фаза строительства: {phase_name}
Дата смены: {shift_date}
Смена: {shift_number}
Участок ПК: с {chainage_start} по {chainage_end}

Контекст из PDF-документа проекта:
---
{pdf_context}
---

На основе этих данных сформируй реалистичный сменный рапорт в JSON:
{{
  "works_done": [
    {{
      "work_type": "наименование вида работ",
      "unit": "шт/м/м²/т",
      "quantity": <число>,
      "chainage": "ПК XX+XX — ПК YY+YY",
      "note": "дополнительная информация"
    }}
  ],
  "workers_on_site": {{
    "ИТР": <число>,
    "рабочие": <число>,
    "охрана": <число>,
    "итого": <число>
  }},
  "machinery_on_site": [
    {{
      "name": "марка и тип машины",
      "reg": "гос. номер",
      "hours_worked": <число>
    }}
  ],
  "materials_received": [
    {{
      "name": "наименование материала",
      "quantity": <число>,
      "unit": "шт/м/т",
      "cert_no": "номер сертификата или пусто"
    }}
  ],
  "quality_checks": [
    {{
      "type": "вид контроля (ВИК, УЗК, РК, пр.)",
      "quantity": <число>,
      "result": "% удовлетворительно / замечания",
      "inspector": "ФИО контролёра"
    }}
  ],
  "downtime_hours": <число>,
  "downtime_reason": "причина простоя или пустая строка",
  "next_shift_plan": "задание на следующую смену",
  "documents_issued": [
    {{
      "type": "АОСР/запись ОЖР/др.",
      "number": "номер документа",
      "work": "на какой вид работ"
    }}
  ]
}}

Учти нормативные требования для фазы '{phase_name}':
{normatives}

Типовая техника для этой фазы: {machinery_hint}
"""


async def _call_claude(prompt: str, system: str = _SYSTEM_PROMPT) -> str:
    """Вызвать Claude API. При ошибке вернуть пустую строку."""
    if settings.OFFLINE_MODE:
        return ""
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception:
        return ""


def _parse_json_from_ai(raw: str) -> dict:
    """Безопасно распарсить JSON из ответа Claude."""
    if not raw:
        return {}
    # Убрать возможные ```json ... ```
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {}


def _build_fallback_report(
    phase: ConstructionPhase,
    chainage_start: str,
    chainage_end: str,
) -> dict:
    """Сформировать структуру рапорта без AI (заглушка)."""
    machinery = [
        {"name": m, "reg": "—", "hours_worked": 8}
        for m in PHASE_TYPICAL_MACHINERY.get(phase, [])
    ]
    aosr_list = [
        {"type": "запись ОЖР", "number": "—", "work": w}
        for w in PHASE_TYPICAL_AOSR.get(phase, ["Работы согласно ППР"])
    ]
    return {
        "works_done": [
            {
                "work_type": PHASE_NAMES_RU.get(phase, phase.value),
                "unit": "м",
                "quantity": 0,
                "chainage": f"{chainage_start} — {chainage_end}",
                "note": "заполните вручную",
            }
        ],
        "workers_on_site": {"ИТР": 3, "рабочие": 20, "охрана": 2, "итого": 25},
        "machinery_on_site": machinery,
        "materials_received": [],
        "quality_checks": [],
        "downtime_hours": 0,
        "downtime_reason": "",
        "next_shift_plan": "Продолжение работ согласно ППР",
        "documents_issued": aosr_list,
    }


async def generate_shift_report_with_ai(
    project: dict,
    phase: ConstructionPhase,
    shift_date: datetime,
    shift_number: ShiftNumber,
    chainage_start: str,
    chainage_end: str,
    pdf_context: str,
) -> dict:
    """
    Сгенерировать данные сменного рапорта через Claude.
    Возвращает словарь с полями рапорта.
    """
    phase_name = PHASE_NAMES_RU.get(phase, phase.value)
    normatives = "\n".join(f"• {n}" for n in PHASE_NORMATIVES.get(phase, []))
    machinery_hint = ", ".join(PHASE_TYPICAL_MACHINERY.get(phase, []))

    prompt = _FILL_REPORT_PROMPT_TEMPLATE.format(
        project_json=json.dumps(project, ensure_ascii=False, indent=2),
        phase_name=phase_name,
        shift_date=shift_date.strftime("%d.%m.%Y"),
        shift_number="Дневная" if shift_number == ShiftNumber.DAY else "Ночная",
        chainage_start=chainage_start,
        chainage_end=chainage_end,
        pdf_context=pdf_context[:3500] if pdf_context else "нет данных",
        normatives=normatives,
        machinery_hint=machinery_hint or "стандартная техника",
    )

    raw = await _call_claude(prompt)
    data = _parse_json_from_ai(raw)

    if not data or "works_done" not in data:
        data = _build_fallback_report(phase, chainage_start, chainage_end)

    return data


async def get_pdf_context_for_phase(
    db: AsyncSession,
    project_id: str,
    phase: ConstructionPhase,
) -> str:
    """
    Выбрать из БД загруженные PDF проекта и извлечь контекст для фазы.
    Берём первые 3 PDF, максимум 4000 символов контекста.
    """
    result = await db.execute(
        select(ProjectPdfUpload)
        .where(ProjectPdfUpload.project_id == project_id)
        .limit(5)
    )
    uploads: list[ProjectPdfUpload] = result.scalars().all()

    if not uploads:
        return ""

    contexts: list[str] = []
    for upload in uploads:
        if upload.extracted_text:
            chunk = get_relevant_context(upload.extracted_text, phase, max_chars=1500)
            if chunk:
                contexts.append(f"[Из файла: {upload.filename}]\n{chunk}")

    return "\n\n".join(contexts)[:4000]


async def summarize_pdf_with_ai(filename: str, text: str) -> str:
    """Попросить Claude составить краткое содержание загруженного PDF."""
    if not text or settings.OFFLINE_MODE:
        return ""

    prompt = (
        f"Файл: {filename}\n\n"
        f"Текст (первые 3000 символов):\n{text[:3000]}\n\n"
        "Составь краткое содержание (5-10 предложений): "
        "тип документа, объект, основные разделы, ключевые параметры."
    )
    system = (
        "Ты — инженер-строитель МГ. Отвечай по-русски, кратко и по существу. "
        "Только текст, без markdown."
    )
    return await _call_claude(prompt, system=system)
