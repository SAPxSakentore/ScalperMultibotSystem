"""
Модель сменного рапорта строительства МГ.
Охватывает весь цикл: геодезическая разбивка → сдача в эксплуатацию.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ConstructionPhase(str, enum.Enum):
    """Последовательные фазы строительства магистрального газопровода."""
    GEODESY_SURVEY       = "geodesy_survey"       # 1. Геодезическая разбивка оси
    CLEARING             = "clearing"             # 2. Расчистка трассы (КРП)
    TOPSOIL_REMOVAL      = "topsoil_removal"      # 3. Снятие растительного слоя
    TRENCH_EXCAVATION    = "trench_excavation"    # 4. Разработка траншеи
    TRENCH_PREPARATION   = "trench_preparation"   # 5. Подготовка основания траншеи
    PIPE_WELDING         = "pipe_welding"         # 6. Сварка секций труб
    PIPE_INSULATION      = "pipe_insulation"      # 7. Изоляция трубопровода
    PIPE_LAYING          = "pipe_laying"          # 8. Укладка в траншею
    TRANSITIONS          = "transitions"          # 9. Переходы (ГНБ / НБ / авто-жд)
    TRENCH_BACKFILL      = "trench_backfill"      # 10. Засыпка траншеи
    BALLASTING           = "ballasting"           # 11. Балластировка (обводнённые)
    VALVE_INSTALLATION   = "valve_installation"   # 12. Монтаж линейной арматуры
    ECP_INSTALLATION     = "ecp_installation"     # 13. Электрохимическая защита
    HYDRAULIC_TEST       = "hydraulic_test"       # 14. Гидравлические испытания
    PURGE_DRY            = "purge_dry"            # 15. Продувка и осушка
    TIGHTNESS_TEST       = "tightness_test"       # 16. Испытание на герметичность
    EXECUTIVE_SURVEY     = "executive_survey"     # 17. Исполнительная съёмка
    RECULTIVATION        = "recultivation"        # 18. Рекультивация
    GAS_START            = "gas_start"            # 19. Пуск газа / комплексные испытания
    COMMISSIONING        = "commissioning"        # 20. Сдача объекта в эксплуатацию


# Русские наименования фаз
PHASE_NAMES_RU = {
    ConstructionPhase.GEODESY_SURVEY:     "Геодезическая разбивка оси газопровода",
    ConstructionPhase.CLEARING:           "Расчистка трассы (КРП)",
    ConstructionPhase.TOPSOIL_REMOVAL:    "Снятие и складирование растительного слоя",
    ConstructionPhase.TRENCH_EXCAVATION:  "Разработка траншеи",
    ConstructionPhase.TRENCH_PREPARATION: "Подготовка основания траншеи (постель)",
    ConstructionPhase.PIPE_WELDING:       "Сварка секций труб",
    ConstructionPhase.PIPE_INSULATION:    "Антикоррозийная изоляция трубопровода",
    ConstructionPhase.PIPE_LAYING:        "Укладка трубопровода в траншею",
    ConstructionPhase.TRANSITIONS:        "Переходы через препятствия (ГНБ / НБ)",
    ConstructionPhase.TRENCH_BACKFILL:    "Засыпка и уплотнение траншеи",
    ConstructionPhase.BALLASTING:         "Балластировка трубопровода",
    ConstructionPhase.VALVE_INSTALLATION: "Монтаж линейной арматуры (краны, КИП)",
    ConstructionPhase.ECP_INSTALLATION:   "Монтаж электрохимической защиты",
    ConstructionPhase.HYDRAULIC_TEST:     "Гидравлические испытания",
    ConstructionPhase.PURGE_DRY:          "Продувка и осушка газопровода",
    ConstructionPhase.TIGHTNESS_TEST:     "Испытание на герметичность",
    ConstructionPhase.EXECUTIVE_SURVEY:   "Исполнительная геодезическая съёмка",
    ConstructionPhase.RECULTIVATION:      "Рекультивация земель",
    ConstructionPhase.GAS_START:          "Пуск газа / комплексные испытания",
    ConstructionPhase.COMMISSIONING:      "Сдача объекта в эксплуатацию",
}

# Типовые НТД для каждой фазы
PHASE_NORMATIVES = {
    ConstructionPhase.GEODESY_SURVEY:     ["СНиП РК 3.01.01-2008*", "ГОСТ Р 51872-2002", "СП РК 1.04.02-2019"],
    ConstructionPhase.CLEARING:           ["СНиП РК 3.01.01-2008*", "ПОС/ППР проекта"],
    ConstructionPhase.TOPSOIL_REMOVAL:    ["СНиП РК 3.01.01-2008*", "ПОС/ППР проекта"],
    ConstructionPhase.TRENCH_EXCAVATION:  ["СНиП РК 3.01.01-2008*", "СП РК 2.04-103-2013*"],
    ConstructionPhase.TRENCH_PREPARATION: ["СП РК 2.04-103-2013*", "ВСН 012-88"],
    ConstructionPhase.PIPE_WELDING:       ["ВСН 012-88", "ГОСТ 16037-80", "РД РК 3.01.001-2019"],
    ConstructionPhase.PIPE_INSULATION:    ["ГОСТ 9.602-2016", "ВСН 012-88 ч.II"],
    ConstructionPhase.PIPE_LAYING:        ["СП РК 2.04-103-2013*", "ВСН 012-88"],
    ConstructionPhase.TRANSITIONS:        ["СП РК 2.04-103-2013*", "ВСН 012-88 ч.III"],
    ConstructionPhase.TRENCH_BACKFILL:    ["СП РК 2.04-103-2013*", "СНиП РК 3.01.01-2008*"],
    ConstructionPhase.BALLASTING:         ["СП РК 2.04-103-2013*"],
    ConstructionPhase.VALVE_INSTALLATION: ["СП РК 2.04-103-2013*", "паспорта оборудования"],
    ConstructionPhase.ECP_INSTALLATION:   ["ГОСТ 9.602-2016", "СП РК 2.04-103-2013* п.11"],
    ConstructionPhase.HYDRAULIC_TEST:     ["СП РК 2.04-103-2013* п.10", "ВСН 012-88 ч.I"],
    ConstructionPhase.PURGE_DRY:          ["СП РК 2.04-103-2013* п.10.5", "ВСН 012-88"],
    ConstructionPhase.TIGHTNESS_TEST:     ["ГОСТ 24054-80", "СП РК 2.04-103-2013* п.10"],
    ConstructionPhase.EXECUTIVE_SURVEY:   ["СП РК 1.04.02-2019", "СНиП РК 3.01.01-2008*"],
    ConstructionPhase.RECULTIVATION:      ["СНиП РК 3.01.01-2008*", "Закон РК об экологии"],
    ConstructionPhase.GAS_START:          ["СП РК 2.04-103-2013* п.11", "ПБ в газовом хозяйстве"],
    ConstructionPhase.COMMISSIONING:      ["СНиП РК 1.01.12-2009", "Закон РК №242-II", "КС-14"],
}

# Типовая техника для каждой фазы
PHASE_TYPICAL_MACHINERY = {
    ConstructionPhase.GEODESY_SURVEY:     ["Теодолит / Total Station", "GPS-приёмник (RTK)", "Нивелир"],
    ConstructionPhase.CLEARING:           ["Бульдозер", "Кусторез", "Корчеватель"],
    ConstructionPhase.TOPSOIL_REMOVAL:    ["Бульдозер", "Скрепер", "Самосвал"],
    ConstructionPhase.TRENCH_EXCAVATION:  ["Одноковшовый экскаватор", "Самосвал", "Бульдозер"],
    ConstructionPhase.TRENCH_PREPARATION: ["Экскаватор", "Бульдозер", "Трамбовка"],
    ConstructionPhase.PIPE_WELDING:       ["Сварочный агрегат", "Центратор внутренний/наружный", "Трубоукладчик"],
    ConstructionPhase.PIPE_INSULATION:    ["Изоляционная машина", "Трубоукладчик", "Тягач"],
    ConstructionPhase.PIPE_LAYING:        ["Трубоукладчик (3–6 шт.)", "Экскаватор", "Бульдозер"],
    ConstructionPhase.TRANSITIONS:        ["Буровая установка ГНБ", "Трубоукладчик", "Кран"],
    ConstructionPhase.TRENCH_BACKFILL:    ["Бульдозер", "Экскаватор", "Виброплита / Каток"],
    ConstructionPhase.BALLASTING:         ["Кран", "Автобетоносмеситель", "Трубоукладчик"],
    ConstructionPhase.VALVE_INSTALLATION: ["Кран", "Автогидроподъёмник", "Сварочный агрегат"],
    ConstructionPhase.ECP_INSTALLATION:   ["Экскаватор", "Сварочный агрегат", "Кабелеукладчик"],
    ConstructionPhase.HYDRAULIC_TEST:     ["Опрессовочный агрегат", "Манометры (класс 0.25)", "Насосная станция"],
    ConstructionPhase.PURGE_DRY:          ["Компрессор", "Осушитель воздуха", "Свечи продувки"],
    ConstructionPhase.TIGHTNESS_TEST:     ["Компрессор", "Манометры", "Течеискатель"],
    ConstructionPhase.EXECUTIVE_SURVEY:   ["Total Station", "GPS RTK", "Нивелир"],
    ConstructionPhase.RECULTIVATION:      ["Бульдозер", "Сеялка", "Поливальная машина"],
    ConstructionPhase.GAS_START:          ["Редуктор давления", "Газоанализатор", "Запорная арматура"],
    ConstructionPhase.COMMISSIONING:      [],
}

# Типовые скрытые работы (АОСР) для каждой фазы
PHASE_TYPICAL_AOSR = {
    ConstructionPhase.TRENCH_EXCAVATION:  ["Разработка траншеи в скальном/мягком грунте"],
    ConstructionPhase.TRENCH_PREPARATION: ["Устройство постели из мягкого грунта"],
    ConstructionPhase.PIPE_WELDING:       ["Сварные стыки трубопровода"],
    ConstructionPhase.PIPE_INSULATION:    ["Антикоррозийная изоляция трубопровода"],
    ConstructionPhase.PIPE_LAYING:        ["Укладка трубопровода в траншею"],
    ConstructionPhase.TRENCH_BACKFILL:    ["Засыпка и уплотнение грунта над трубопроводом"],
    ConstructionPhase.ECP_INSTALLATION:   ["Монтаж протекторной (катодной) защиты"],
}


class ShiftNumber(str, enum.Enum):
    DAY   = "day"    # Дневная смена
    NIGHT = "night"  # Ночная смена


class ShiftReport(Base):
    """Сменный производственный рапорт строительства МГ."""
    __tablename__ = "shift_reports"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)

    # Идентификация смены
    shift_date   = Column(DateTime, nullable=False, default=datetime.utcnow)
    shift_number = Column(Enum(ShiftNumber), default=ShiftNumber.DAY)
    shift_foreman = Column(String(200))   # Прораб / начальник смены

    # Фаза строительства
    construction_phase = Column(Enum(ConstructionPhase), nullable=False)

    # Участок работ
    chainage_start = Column(String(50))   # ПК начало
    chainage_end   = Column(String(50))   # ПК конец
    length_done_m  = Column(Float, default=0.0)  # Выполнено, м

    # Погода
    weather_morning   = Column(String(100))  # t°C, ветер, осадки
    weather_afternoon = Column(String(100))

    # Выполненные работы за смену (структурированный список)
    works_done = Column(JSON, default=list)
    # [{
    #   "work_type": "Сварка стыков",
    #   "unit": "шт",
    #   "quantity": 12,
    #   "chainage": "ПК 14+00 — ПК 15+20",
    #   "note": "клеймо С-47",
    # }]

    # Ресурсы
    workers_on_site  = Column(JSON, default=dict)
    # {"ИТР": 3, "рабочие": 24, "охрана": 2, "итого": 29}
    machinery_on_site = Column(JSON, default=list)
    # [{"name": "Экскаватор Hyundai 220", "reg": "123 QAZ", "hours_worked": 8}]

    # Поставки материалов за смену
    materials_received = Column(JSON, default=list)
    # [{"name": "Труба DN1020 × 14", "quantity": 5, "unit": "шт", "cert_no": "..."}]

    # Контроль качества
    quality_checks = Column(JSON, default=list)
    # [{"type": "ВИК сварных стыков", "quantity": 12, "result": "100% удовл.", "inspector": "..."}]

    # Простои и нарушения
    downtime_hours   = Column(Float, default=0.0)
    downtime_reason  = Column(Text)
    safety_incidents = Column(Text)  # НС / замечания HSE

    # Выданные документы за смену
    documents_issued = Column(JSON, default=list)
    # [{"type": "АОСР", "number": "001", "work": "Сварка стыков"}]

    # Задание на следующую смену
    next_shift_plan = Column(Text)

    # AI-генерация
    ai_generated = Column(Boolean, default=False)
    ai_prompt_context = Column(Text)  # фрагмент из PDF проекта, использованный для генерации

    # Финализация
    is_finalized = Column(Boolean, default=False)
    signed_by    = Column(String(200))
    signed_at    = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="shift_reports")


class ProjectPdfUpload(Base):
    """Загруженные PDF-файлы проекта (ПОС, ППР, ПД, ПНД и т.д.)."""
    __tablename__ = "project_pdf_uploads"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)

    filename        = Column(String(500), nullable=False)
    file_path       = Column(String(500), nullable=False)
    doc_category    = Column(String(100))    # ПОС / ППР / ПД / НТД / прочее
    page_count      = Column(Integer, default=0)
    extracted_text  = Column(Text)           # Весь текст из PDF
    text_summary    = Column(Text)           # Краткое содержание (Claude)
    construction_phases_mentioned = Column(JSON, default=list)  # Фазы из PDF

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="pdf_uploads")
