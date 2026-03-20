"""
Сервис автоматической генерации ИТД (исполнительно-технической документации).
Генерирует документы в форматах DOCX.
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from app.core.config import settings


def _set_table_borders(table):
    """Добавить границы ко всем ячейкам таблицы."""
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                border = OxmlElement(f'w:{border_name}')
                border.set(qn('w:val'), 'single')
                border.set(qn('w:sz'), '4')
                border.set(qn('w:space'), '0')
                border.set(qn('w:color'), '000000')
                tcBorders.append(border)
            tcPr.append(tcBorders)


class DocumentGenerator:
    """Генератор ИТД для строительных проектов РК."""

    def __init__(self):
        self.storage_path = settings.DOCS_STORAGE_PATH
        os.makedirs(self.storage_path, exist_ok=True)

    def _save_document(self, doc: Document, doc_type: str, project_code: str) -> str:
        """Сохранить документ и вернуть путь."""
        filename = f"{doc_type}_{project_code}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d')}.docx"
        file_path = os.path.join(self.storage_path, filename)
        doc.save(file_path)
        return file_path

    def generate_ojr(self, project_data: Dict, entries: list = None) -> str:
        """
        Генерация Общего журнала работ (ОЖР).
        СП РК 1.04.02-2019
        """
        doc = Document()

        # Настройка страницы
        section = doc.sections[0]
        section.page_width = Cm(29.7)
        section.page_height = Cm(21.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.5)

        # Заголовок
        title = doc.add_heading("ОБЩИЙ ЖУРНАЛ РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub = doc.add_paragraph("(СП РК 1.04.02-2019)")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()

        # Данные объекта
        info_table = doc.add_table(rows=7, cols=2)
        info_table.style = 'Table Grid'
        _set_table_borders(info_table)

        fields = [
            ("Наименование объекта:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Генподрядчик:", project_data.get("contractor_name", "")),
            ("Проектировщик:", project_data.get("designer_name", "")),
            ("Начало строительства:", project_data.get("start_date", "")),
            ("Технический надзор:", project_data.get("technical_supervisor", "")),
        ]

        for i, (label, value) in enumerate(fields):
            row = info_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = str(value) if value else ""
            row.cells[0].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()

        # Заголовок раздела записей
        section_title = doc.add_heading("РАЗДЕЛ 1. СПИСОК ЛИЦ, ОСУЩЕСТВЛЯЮЩИХ СТРОИТЕЛЬСТВО", level=2)

        doc.add_paragraph()

        # Таблица записей
        header = doc.add_heading("РАЗДЕЛ 3. СВЕДЕНИЯ О ПРОИЗВОДСТВЕ РАБОТ", level=2)
        doc.add_paragraph()

        entries_table = doc.add_table(rows=1, cols=6)
        entries_table.style = 'Table Grid'
        _set_table_borders(entries_table)

        header_row = entries_table.rows[0]
        headers = ["№ п/п", "Дата", "Описание выполненных работ", "ПК (пикет)", "Исполнитель", "Примечание"]
        for i, h in enumerate(headers):
            cell = header_row.cells[i]
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        if entries:
            for idx, entry in enumerate(entries, 1):
                row = entries_table.add_row()
                row.cells[0].text = str(idx)
                row.cells[1].text = entry.get("date", "")
                row.cells[2].text = entry.get("description", "")
                row.cells[3].text = entry.get("chainage", "")
                row.cells[4].text = entry.get("foreman", "")
                row.cells[5].text = entry.get("note", "")
        else:
            # Пустая строка
            entries_table.add_row()

        return self._save_document(doc, "OJR", project_data.get("code", "PROJ"))

    def generate_aosr(self, project_data: Dict, work_data: Dict) -> str:
        """
        Генерация Акта освидетельствования скрытых работ (АОСР).
        СП РК 1.04.02-2019
        """
        doc = Document()

        # Заголовок
        title = doc.add_heading("АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(f"№ {work_data.get('act_number', '____')}").bold = True

        doc.add_paragraph(
            f"«{work_data.get('date', datetime.now().strftime('%d'))}» "
            f"{_month_ru(datetime.now().month)} "
            f"{datetime.now().year} г."
        ).alignment = WD_ALIGN_PARAGRAPH.RIGHT

        doc.add_paragraph()

        # Стороны
        doc.add_paragraph(
            f"Представитель заказчика — технический надзор: "
            f"{project_data.get('technical_supervisor', '____________________')}"
        )
        doc.add_paragraph(
            f"Представитель подрядчика — производитель работ: "
            f"{work_data.get('foreman', '____________________')}"
        )
        doc.add_paragraph(
            f"Представитель проектировщика — авторский надзор: "
            f"{work_data.get('author_supervisor', '____________________')}"
        )

        doc.add_paragraph()

        # Основная часть
        doc.add_heading("1. Предъявлены к освидетельствованию:", level=2)
        doc.add_paragraph(
            f"Работы: {work_data.get('work_name', '____________________')}\n"
            f"Объект: {project_data.get('name', '')}\n"
            f"Участок (ПК): {work_data.get('chainage', '____________________')}\n"
            f"Дата выполнения: {work_data.get('work_date', '____________________')}"
        )

        doc.add_heading("2. Работы выполнены по проектной документации:", level=2)
        doc.add_paragraph(
            f"Шифр проекта: {project_data.get('code', '____________________')}\n"
            f"Раздел: {work_data.get('design_section', '____________________')}\n"
            f"Разработчик: {project_data.get('designer_name', '____________________')}"
        )

        doc.add_heading("3. Применены материалы:", level=2)
        materials = work_data.get("materials", [])
        if materials:
            for mat in materials:
                doc.add_paragraph(f"• {mat}", style="List Bullet")
        else:
            doc.add_paragraph("Согласно проекту и сертификатам качества.")

        doc.add_heading("4. Нормативные документы:", level=2)
        normatives = work_data.get("normatives", ["СП РК 2.04-103-2013*", "СП РК 1.04.02-2019"])
        for norm in normatives:
            doc.add_paragraph(f"• {norm}", style="List Bullet")

        doc.add_heading("5. Заключение:", level=2)
        doc.add_paragraph(
            f"Работы выполнены в соответствии с проектной документацией, "
            f"требованиями нормативных технических документов и технических условий.\n\n"
            f"Разрешается производство последующих работ: "
            f"{work_data.get('next_works', '____________________')}"
        )

        doc.add_paragraph()
        doc.add_paragraph()

        # Подписи
        signs_table = doc.add_table(rows=3, cols=3)
        signs_table.style = 'Table Grid'
        rows = signs_table.rows
        roles = ["Технический надзор", "Авторский надзор", "Производитель работ"]
        names = [
            project_data.get("technical_supervisor", ""),
            work_data.get("author_supervisor", ""),
            work_data.get("foreman", ""),
        ]
        for i, (role, name) in enumerate(zip(roles, names)):
            r = signs_table.rows[i]
            r.cells[0].text = role
            r.cells[1].text = "____________"
            r.cells[2].text = name

        return self._save_document(doc, "AOSR", project_data.get("code", "PROJ"))

    def generate_hydraulic_test_act(self, project_data: Dict, test_data: Dict) -> str:
        """
        Акт гидравлических испытаний трубопровода.
        СП РК 2.04-103-2013*
        """
        doc = Document()

        title = doc.add_heading("АКТ ГИДРАВЛИЧЕСКИХ ИСПЫТАНИЙ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(
            f"ТРУБОПРОВОДА НА ПРОЧНОСТЬ И ГЕРМЕТИЧНОСТЬ"
        ).alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()

        doc.add_paragraph(
            f"Объект: {project_data.get('name', '')}\n"
            f"Заказчик: {project_data.get('customer_name', '')}\n"
            f"Подрядчик: {project_data.get('contractor_name', '')}\n"
            f"Дата испытания: {test_data.get('test_date', datetime.now().strftime('%d.%m.%Y'))}"
        )

        doc.add_paragraph()
        doc.add_heading("ХАРАКТЕРИСТИКИ ИСПЫТУЕМОГО УЧАСТКА:", level=2)

        params_table = doc.add_table(rows=8, cols=2)
        params_table.style = 'Table Grid'
        _set_table_borders(params_table)

        params = [
            ("Участок трубопровода (ПК):", test_data.get("section_chainage", "")),
            ("Длина испытуемого участка:", f"{test_data.get('length_m', '')} м"),
            ("Диаметр трубы:", f"{project_data.get('diameter_mm', '')} мм"),
            ("Толщина стенки:", f"{test_data.get('wall_thickness_mm', '')} мм"),
            ("Марка стали:", test_data.get("steel_grade", "")),
            ("Рабочее давление:", f"{project_data.get('working_pressure_mpa', '')} МПа"),
            ("Испытательное давление (прочность):", f"{test_data.get('test_pressure_mpa', '')} МПа"),
            ("Испытательное давление (герметичность):", f"{test_data.get('tightness_pressure_mpa', '')} МПа"),
        ]

        for i, (label, value) in enumerate(params):
            row = params_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = str(value)

        doc.add_paragraph()
        doc.add_heading("РЕЗУЛЬТАТЫ ИСПЫТАНИЯ:", level=2)

        results_table = doc.add_table(rows=4, cols=2)
        results_table.style = 'Table Grid'
        _set_table_borders(results_table)

        results = [
            ("Давление в начале испытания:", f"{test_data.get('pressure_start', '')} МПа"),
            ("Давление в конце испытания:", f"{test_data.get('pressure_end', '')} МПа"),
            ("Время выдержки:", f"{test_data.get('duration_hours', 24)} часов"),
            ("Результат:", test_data.get("result", "УДОВЛЕТВОРИТЕЛЬНО — трубопровод выдержал испытание")),
        ]

        for i, (label, value) in enumerate(results):
            row = results_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = str(value)

        doc.add_paragraph()
        doc.add_paragraph(
            f"ЗАКЛЮЧЕНИЕ: Трубопровод {test_data.get('section_chainage', 'участок')} "
            f"выдержал гидравлическое испытание на прочность давлением "
            f"{test_data.get('test_pressure_mpa', '')} МПа и на герметичность давлением "
            f"{test_data.get('tightness_pressure_mpa', '')} МПа. "
            f"Трубопровод к дальнейшему строительству допускается."
        )

        doc.add_paragraph()
        doc.add_paragraph("Нормативный документ: СП РК 2.04-103-2013*, п. 10.3")

        return self._save_document(doc, "HydraulicTest", project_data.get("code", "PROJ"))

    def generate_ks11(self, project_data: Dict) -> str:
        """
        Акт приемки построенного объекта строительства (КС-11).
        """
        doc = Document()

        title = doc.add_heading("АКТ ПРИЕМКИ ПОСТРОЕННОГО ОБЪЕКТА СТРОИТЕЛЬСТВА", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitle = doc.add_paragraph("(Форма КС-11)")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()

        doc.add_paragraph(
            f"г. {project_data.get('region', 'Алматы')}    "
            f"«____» _________ {datetime.now().year} г."
        )

        doc.add_paragraph()

        doc.add_paragraph(
            f"Заказчик: {project_data.get('customer_name', '')}\n"
            f"Генеральный подрядчик: {project_data.get('contractor_name', '')}"
        )

        doc.add_paragraph()
        doc.add_paragraph(
            "составили настоящий акт о нижеследующем:"
        )

        doc.add_heading("1. Наименование объекта:", level=2)
        doc.add_paragraph(project_data.get("name", ""))

        doc.add_heading("2. Местонахождение объекта:", level=2)
        doc.add_paragraph(
            f"{project_data.get('region', '')}, {project_data.get('district', '')}, "
            f"{project_data.get('locality', '')}"
        )

        doc.add_heading("3. Основные технические характеристики:", level=2)
        tech_table = doc.add_table(rows=4, cols=2)
        tech_table.style = 'Table Grid'
        _set_table_borders(tech_table)

        tech_params = [
            ("Протяженность трубопровода:", f"{project_data.get('total_length_km', '')} км"),
            ("Диаметр:", f"{project_data.get('diameter_mm', '')} мм"),
            ("Рабочее давление:", f"{project_data.get('working_pressure_mpa', '')} МПа"),
            ("Шифр проекта:", project_data.get("code", "")),
        ]
        for i, (label, value) in enumerate(tech_params):
            row = tech_table.rows[i]
            row.cells[0].text = label
            row.cells[1].text = str(value)

        doc.add_heading("4. Сроки строительства:", level=2)
        doc.add_paragraph(
            f"Начало: {project_data.get('start_date', '____________________')}\n"
            f"Окончание: {project_data.get('actual_end_date', '____________________')}"
        )

        doc.add_heading("5. Соответствие нормативам:", level=2)
        doc.add_paragraph(
            "Объект построен в соответствии с проектной документацией, "
            "требованиями СП РК 2.04-103-2013*, СНиП РК 1.01.12-2009 "
            "и другими нормативными документами Республики Казахстан."
        )

        doc.add_paragraph()
        doc.add_paragraph(
            "Объект принят в полном объеме и пригоден к эксплуатации."
        ).runs[0].bold = True

        doc.add_paragraph()

        # Подписи
        for role, name_field in [
            ("Заказчик:", "customer_name"),
            ("Генеральный подрядчик:", "contractor_name"),
        ]:
            p = doc.add_paragraph()
            p.add_run(role).bold = True
            p.add_run(f" {project_data.get(name_field, '')}")
            doc.add_paragraph("Подпись: ____________ М.П.")
            doc.add_paragraph()

        return self._save_document(doc, "KS11", project_data.get("code", "PROJ"))


def _month_ru(month: int) -> str:
    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    return months.get(month, "")


# Синглтон генератора
document_generator = DocumentGenerator()
