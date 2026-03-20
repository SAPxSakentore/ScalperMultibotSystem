"""
Нормативная база строительства Республики Казахстан.
СП РК, СНиП РК, ГОСТ, отраслевые нормы для газопроводов.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class NormativeDocument:
    code: str
    title: str
    category: str
    applies_to: List[str]
    key_requirements: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None


# ============================================================
# НОРМАТИВНАЯ БАЗА РК — МАГИСТРАЛЬНЫЕ ГАЗОПРОВОДЫ
# ============================================================

NORMATIVE_DB: Dict[str, NormativeDocument] = {

    # === СП РК (Строительные правила) ===
    "SP_RK_2.04-103": NormativeDocument(
        code="СП РК 2.04-103-2013*",
        title="Магистральные трубопроводы",
        category="СП РК",
        applies_to=["gas_pipeline_high", "oil_pipeline"],
        key_requirements={
            "depth_cover_normal": "Глубина укладки от верха трубы не менее 0.8 м (нормальные условия)",
            "depth_cover_transport": "Глубина укладки не менее 1.0 м под дорогами",
            "test_pressure_hydraulic": "Гидравлическое испытание: 1.25 × рабочее давление, не менее 1 часа",
            "test_pressure_pneumatic": "Пневматическое испытание: 1.1 × рабочее давление",
            "cathodic_protection": "Обязательная электрохимическая защита от коррозии",
            "isolation_class": "Усиленная изоляция в пределах населенных пунктов",
            "marker_spacing": "Знаки обозначения трассы через 500 м на прямых участках",
            "valve_spacing_uninhabited": "Линейные краны: не более 30 км в ненаселенной местности",
            "valve_spacing_inhabited": "Линейные краны: не более 15 км вблизи населенных пунктов",
        }
    ),

    "SP_RK_1.04.01": NormativeDocument(
        code="СП РК 1.04.01-2018",
        title="Строительный контроль. Порядок осуществления строительного контроля",
        category="СП РК",
        applies_to=["all"],
        key_requirements={
            "technical_supervision": "Технический надзор заказчика обязателен на весь период строительства",
            "author_supervision": "Авторский надзор проектировщика обязателен для объектов I и II категорий",
            "hidden_works": "Скрытые работы оформляются актом до начала последующих работ",
            "incoming_control": "Входной контроль материалов и оборудования обязателен",
        }
    ),

    "SP_RK_1.04.02": NormativeDocument(
        code="СП РК 1.04.02-2019",
        title="Исполнительная техническая документация в строительстве",
        category="СП РК",
        applies_to=["all"],
        key_requirements={
            "ojr": "Общий журнал работ ведется с первого рабочего дня на объекте",
            "aosr_timing": "АОСР оформляется до засыпки/закрытия скрытых работ",
            "executive_schemes": "Исполнительные схемы составляются в процессе строительства",
            "as_built": "Исполнительная документация сдается заказчику при приемке объекта",
        }
    ),

    "SP_RK_4.03.01": NormativeDocument(
        code="СП РК 4.03.01-2012*",
        title="Газоснабжение. Внутренние устройства",
        category="СП РК",
        applies_to=["gas_pipeline_medium", "gas_pipeline_low"],
        key_requirements={
            "low_pressure_max": "Низкое давление: до 0.005 МПа",
            "medium_pressure_max": "Среднее давление: свыше 0.005 до 0.3 МПа",
            "high_pressure_max": "Высокое давление: свыше 0.3 до 1.2 МПа",
        }
    ),

    # === СНиП РК ===
    "SNIP_RK_3.01.01": NormativeDocument(
        code="СНиП РК 3.01.01-2008*",
        title="Организация строительного производства",
        category="СНиП РК",
        applies_to=["all"],
        key_requirements={
            "pos_required": "ПОС разрабатывается в составе проектной документации",
            "ppr_required": "ППР разрабатывается до начала работ (подрядчик)",
            "construction_passport": "Строительный паспорт объекта оформляется до начала работ",
        }
    ),

    "SNIP_RK_1.01.12": NormativeDocument(
        code="СНиП РК 1.01.12-2009",
        title="Строительство. Основные положения",
        category="СНиП РК",
        applies_to=["all"],
        key_requirements={
            "categories": "Объекты строительства I, II, III категорий ответственности",
            "acceptance": "Приемка объектов в эксплуатацию — КС-14 (приемочная комиссия)",
        }
    ),

    # === ГОСТ (действующие в РК) ===
    "GOST_R_ISO_3183": NormativeDocument(
        code="ГОСТ Р ИСО 3183-2009",
        title="Трубы стальные для трубопроводов нефтяной и газовой промышленности",
        category="ГОСТ",
        applies_to=["gas_pipeline_high", "oil_pipeline"],
        key_requirements={
            "pipe_class_high": "Класс прочности К52, К55, К60 для магистральных газопроводов",
            "wall_thickness": "Расчет толщины стенки по максимальному давлению",
        }
    ),

    "GOST_16037": NormativeDocument(
        code="ГОСТ 16037-80",
        title="Соединения сварные стальных трубопроводов. Основные типы",
        category="ГОСТ",
        applies_to=["gas_pipeline_high", "gas_pipeline_medium", "oil_pipeline"],
        key_requirements={
            "weld_types": "Стыковые сварные соединения: С2, С4, С17 и др.",
            "control": "100% контроль сварных стыков магистральных газопроводов",
        }
    ),

    "GOST_9.602": NormativeDocument(
        code="ГОСТ 9.602-2016",
        title="Сооружения подземные. Защита от коррозии",
        category="ГОСТ",
        applies_to=["gas_pipeline_high", "gas_pipeline_medium", "oil_pipeline"],
        key_requirements={
            "isolation_types": "Нормальная, усиленная, весьма усиленная изоляция",
            "eps_test": "Проверка сплошности изоляционного покрытия искровым дефектоскопом",
        }
    ),

    "GOST_24054": NormativeDocument(
        code="ГОСТ 24054-80",
        title="Изделия машиностроения и приборостроения. Методы испытаний на герметичность",
        category="ГОСТ",
        applies_to=["gas_pipeline_high", "gas_pipeline_medium"],
        key_requirements={
            "pneumatic_duration": "Время выдержки при пневматическом испытании — не менее 30 мин",
        }
    ),

    # === РД (Руководящие документы) ===
    "RD_3.01.001": NormativeDocument(
        code="РД РК 3.01.001-2019",
        title="Требования к квалификации сварщиков при строительстве трубопроводов",
        category="РД",
        applies_to=["gas_pipeline_high", "oil_pipeline"],
        key_requirements={
            "welder_cert": "Сварщики должны иметь действующую аттестацию НАКС РК",
            "test_joint": "Сварщик допускается после успешной сварки допускного стыка",
        }
    ),

    # === Закон РК ===
    "LAW_ARCH": NormativeDocument(
        code="Закон РК от 16.07.2001 №242-II",
        title="Об архитектурной, градостроительной и строительной деятельности в РК",
        category="Закон",
        applies_to=["all"],
        key_requirements={
            "permit": "Разрешение на строительство обязательно для объектов I и II категорий",
            "acceptance_commission": "Создание приемочной комиссии по приказу местного исполнительного органа",
            "gia": "Государственная исходно-разрешительная документация (ГИРД)",
        }
    ),
}


def get_normative_for_project_type(project_type: str) -> List[NormativeDocument]:
    """Получить список НТД для данного типа проекта."""
    result = []
    for doc in NORMATIVE_DB.values():
        if "all" in doc.applies_to or project_type in doc.applies_to:
            result.append(doc)
    return result


def get_normative_by_code(code: str) -> Optional[NormativeDocument]:
    """Найти нормативный документ по коду."""
    for doc in NORMATIVE_DB.values():
        if doc.code.upper() == code.upper() or doc.code.upper().startswith(code.upper()):
            return doc
    return None


def get_normative_summary_for_prompt(project_type: str) -> str:
    """Формирует текстовую выжимку НТД для передачи в system prompt агента."""
    docs = get_normative_for_project_type(project_type)
    lines = ["=== ПРИМЕНИМАЯ НОРМАТИВНАЯ БАЗА РК ===\n"]
    for doc in docs:
        lines.append(f"📋 {doc.code}: {doc.title}")
        for key, val in doc.key_requirements.items():
            lines.append(f"   • {val}")
        lines.append("")
    return "\n".join(lines)


# Перечень ИТД для газопровода высокого давления
ITD_CHECKLIST_GAS_HIGH = [
    {
        "doc_type": "building_passport",
        "name": "Строительный паспорт объекта",
        "normative": "СНиП РК 3.01.01-2008*, Закон РК №242-II",
        "phase": "initiation",
        "required": True,
    },
    {
        "doc_type": "pos",
        "name": "Проект организации строительства (ПОС)",
        "normative": "СНиП РК 3.01.01-2008*",
        "phase": "design",
        "required": True,
    },
    {
        "doc_type": "ppr",
        "name": "Проект производства работ (ППР)",
        "normative": "СНиП РК 3.01.01-2008*",
        "phase": "construction",
        "required": True,
    },
    {
        "doc_type": "ojr",
        "name": "Общий журнал работ",
        "normative": "СП РК 1.04.02-2019",
        "phase": "construction",
        "required": True,
    },
    {
        "doc_type": "welding_journal",
        "name": "Журнал сварочных работ",
        "normative": "СП РК 2.04-103-2013*",
        "phase": "construction",
        "required": True,
    },
    {
        "doc_type": "isolation_journal",
        "name": "Журнал изоляционных работ",
        "normative": "ГОСТ 9.602-2016",
        "phase": "construction",
        "required": True,
    },
    {
        "doc_type": "aosr",
        "name": "Акты освидетельствования скрытых работ (АОСР)",
        "normative": "СП РК 1.04.02-2019",
        "phase": "construction",
        "required": True,
        "note": "Оформляется на каждый скрытый вид работ: земляные работы, укладка трубы, засыпка",
    },
    {
        "doc_type": "material_cert",
        "name": "Сертификаты на трубы и фитинги",
        "normative": "ГОСТ Р ИСО 3183-2009",
        "phase": "procurement",
        "required": True,
    },
    {
        "doc_type": "welder_cert",
        "name": "Удостоверения сварщиков (НАКС РК)",
        "normative": "РД РК 3.01.001-2019",
        "phase": "construction",
        "required": True,
    },
    {
        "doc_type": "executive_scheme",
        "name": "Исполнительные схемы укладки трубопровода",
        "normative": "СП РК 1.04.02-2019",
        "phase": "construction",
        "required": True,
    },
    {
        "doc_type": "hydraulic_test",
        "name": "Акт гидравлических испытаний",
        "normative": "СП РК 2.04-103-2013*",
        "phase": "testing",
        "required": True,
        "note": "Давление: 1.25 × рабочее, время выдержки — 24 часа",
    },
    {
        "doc_type": "tightness_test",
        "name": "Акт испытания на герметичность",
        "normative": "ГОСТ 24054-80, СП РК 2.04-103-2013*",
        "phase": "testing",
        "required": True,
    },
    {
        "doc_type": "purge_act",
        "name": "Акт продувки газопровода",
        "normative": "СП РК 2.04-103-2013*",
        "phase": "commissioning",
        "required": True,
    },
    {
        "doc_type": "ks2",
        "name": "Акты приемки выполненных работ (КС-2)",
        "normative": "Постановление Правительства РК",
        "phase": "acceptance",
        "required": True,
    },
    {
        "doc_type": "ks3",
        "name": "Справки о стоимости выполненных работ (КС-3)",
        "normative": "Постановление Правительства РК",
        "phase": "acceptance",
        "required": True,
    },
    {
        "doc_type": "ks11",
        "name": "Акт приемки построенного объекта (КС-11)",
        "normative": "СНиП РК 1.01.12-2009",
        "phase": "acceptance",
        "required": True,
    },
    {
        "doc_type": "ks14",
        "name": "Акт приемочной комиссии (КС-14)",
        "normative": "Закон РК №242-II, СНиП РК 1.01.12-2009",
        "phase": "acceptance",
        "required": True,
    },
]


ITD_CHECKLISTS = {
    "gas_pipeline_high": ITD_CHECKLIST_GAS_HIGH,
    "gas_pipeline_medium": ITD_CHECKLIST_GAS_HIGH,  # аналогичный перечень
    "oil_pipeline": ITD_CHECKLIST_GAS_HIGH,          # аналогичный перечень
}
