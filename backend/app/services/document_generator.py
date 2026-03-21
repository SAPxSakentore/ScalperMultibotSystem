"""
Сервис автоматической генерации ИТД (исполнительно-технической документации).
Генерирует документы в форматах DOCX.
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

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
        normatives = work_data.get("normatives") or ["ВСН 012-88", "СП РК 2.04-103-2013*", "СП РК 1.04.02-2019"]
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
            project_data.get("technical_supervisor") or "",
            work_data.get("author_supervisor") or "",
            work_data.get("foreman") or "",
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

    def generate_isolation_journal(self, project_data: Dict, entries: List = None) -> str:
        """
        Журнал производства изоляционных работ.
        ГОСТ 9.602-2016, ВСН 012-88 ч.II
        """
        doc = Document()
        section = doc.sections[0]
        section.page_width  = Cm(29.7)
        section.page_height = Cm(21.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.0)

        title = doc.add_heading("ЖУРНАЛ ПРОИЗВОДСТВА ИЗОЛЯЦИОННЫХ РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("(ГОСТ 9.602-2016, ВСН 012-88 ч.II)").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        info = doc.add_table(rows=6, cols=2)
        info.style = "Table Grid"
        _set_table_borders(info)
        for i, (lbl, val) in enumerate([
            ("Наименование объекта:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Диаметр трубопровода:", f"DN{project_data.get('diameter_mm', '—')} мм"),
            ("Нормативный документ:", "ГОСТ 9.602-2016, ВСН 012-88 ч.II"),
        ]):
            r = info.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val) if val else "—"

        doc.add_paragraph()

        tbl = doc.add_table(rows=1, cols=10)
        tbl.style = "Table Grid"
        _set_table_borders(tbl)
        headers = [
            "№ п/п", "Дата", "ПК (пикет)", "Вид покрытия", "Тип ленты/мат-ла",
            "Толщина покрытия, мм", "Напряжение дефектоскопа, В", "Результат контроля",
            "Температура, °C", "Исполнитель",
        ]
        hrow = tbl.rows[0]
        for j, h in enumerate(headers):
            hrow.cells[j].text = h
            hrow.cells[j].paragraphs[0].runs[0].bold = True
            hrow.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for idx, e in enumerate(entries or [], 1):
            row = tbl.add_row()
            row.cells[0].text  = str(idx)
            row.cells[1].text  = e.get("date", "")
            row.cells[2].text  = e.get("chainage", "")
            row.cells[3].text  = e.get("coating_type", "2-слойная ПЭ лента")
            row.cells[4].text  = e.get("material", "")
            row.cells[5].text  = e.get("thickness_mm", "")
            row.cells[6].text  = e.get("spark_test_v", "5000")
            row.cells[7].text  = e.get("result", "Удовл.")
            row.cells[8].text  = e.get("temp_c", "")
            row.cells[9].text  = e.get("executor", "")

        if not entries:
            tbl.add_row()

        doc.add_paragraph()
        doc.add_paragraph("Мастер изоляционных работ: _________________ / _________________ / «___» ________ ___ г.")

        return self._save_document(doc, "IsolationJournal", project_data.get("code", "PROJ"))

    def generate_geodesy_journal(self, project_data: Dict, entries: List = None) -> str:
        """
        Геодезический журнал производства работ.
        СНиП РК 3.01.01-2008*, СП РК 1.04.02-2019
        """
        doc = Document()
        section = doc.sections[0]
        section.page_width  = Cm(29.7)
        section.page_height = Cm(21.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.0)

        title = doc.add_heading("ГЕОДЕЗИЧЕСКИЙ ЖУРНАЛ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("(СНиП РК 3.01.01-2008*, СП РК 1.04.02-2019)").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        info = doc.add_table(rows=5, cols=2)
        info.style = "Table Grid"
        _set_table_borders(info)
        for i, (lbl, val) in enumerate([
            ("Наименование объекта:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Ответственный геодезист:", "___________________"),
        ]):
            r = info.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val) if val else "—"

        doc.add_paragraph()

        tbl = doc.add_table(rows=1, cols=9)
        tbl.style = "Table Grid"
        _set_table_borders(tbl)
        headers = [
            "№ п/п", "Дата", "№ разбивочного элемента", "ПК (пикет)",
            "Координата X", "Координата Y", "Отметка (Z), м",
            "Отклонение от проекта", "Примечание",
        ]
        hrow = tbl.rows[0]
        for j, h in enumerate(headers):
            hrow.cells[j].text = h
            hrow.cells[j].paragraphs[0].runs[0].bold = True
            hrow.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for idx, e in enumerate(entries or [], 1):
            row = tbl.add_row()
            row.cells[0].text = str(idx)
            row.cells[1].text = e.get("date", "")
            row.cells[2].text = e.get("element_no", "")
            row.cells[3].text = e.get("chainage", "")
            row.cells[4].text = e.get("x", "")
            row.cells[5].text = e.get("y", "")
            row.cells[6].text = e.get("z", "")
            row.cells[7].text = e.get("deviation", "в норме")
            row.cells[8].text = e.get("note", "")

        if not entries:
            tbl.add_row()

        doc.add_paragraph()
        doc.add_paragraph("Геодезист: _________________ / _________________ / «___» ________ ___ г.")

        return self._save_document(doc, "GeodesyJournal", project_data.get("code", "PROJ"))

    def generate_ks3(self, project_data: Dict, ks3_data: Dict) -> str:
        """
        Справка о стоимости выполненных работ и затрат (КС-3).
        Форма утверждена приказом МФ РК.
        """
        doc = Document()

        title = doc.add_heading("СПРАВКА О СТОИМОСТИ ВЫПОЛНЕННЫХ РАБОТ И ЗАТРАТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub = doc.add_paragraph("(Форма КС-3)")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"г. {project_data.get('region', '')}    «___» _________ {datetime.now().year} г."
        )
        doc.add_paragraph()

        req = doc.add_table(rows=5, cols=2)
        req.style = "Table Grid"
        _set_table_borders(req)
        for i, (lbl, val) in enumerate([
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Объект:", project_data.get("name", "")),
            ("Отчётный период:", ks3_data.get("period", "________________")),
            ("Номер договора подряда:", ks3_data.get("contract_number", "_______________")),
        ]):
            r = req.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Стоимость выполненных работ:", level=2)

        cost_tbl = doc.add_table(rows=1, cols=5)
        cost_tbl.style = "Table Grid"
        _set_table_borders(cost_tbl)
        for j, h in enumerate(["№", "Наименование затрат", "Сметная стоимость, тг.", "С начала строительства, тг.", "В т.ч. за отчётный период, тг."]):
            cost_tbl.rows[0].cells[j].text = h
            cost_tbl.rows[0].cells[j].paragraphs[0].runs[0].bold = True

        items = ks3_data.get("items", [])
        total_period = 0.0
        for idx, item in enumerate(items, 1):
            row = cost_tbl.add_row()
            period_amt = float(item.get("period_amount", 0) or 0)
            total_period += period_amt
            row.cells[0].text = str(idx)
            row.cells[1].text = item.get("name", "")
            row.cells[2].text = f"{float(item.get('budget_amount', 0) or 0):,.2f}"
            row.cells[3].text = f"{float(item.get('cumulative_amount', 0) or 0):,.2f}"
            row.cells[4].text = f"{period_amt:,.2f}"

        if not items:
            cost_tbl.add_row()
            total_period = float(ks3_data.get("total_period", 0) or 0)

        total_row = cost_tbl.add_row()
        total_row.cells[1].text = "ИТОГО:"
        total_row.cells[1].paragraphs[0].runs[0].bold = True
        total_row.cells[4].text = f"{total_period:,.2f} тг."
        total_row.cells[4].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()
        nds = total_period * 0.12
        doc.add_paragraph(
            f"В том числе НДС (12%): {nds:,.2f} тг.\n"
            f"Итого с НДС: {total_period + nds:,.2f} тг."
        ).runs[0].bold = True

        doc.add_paragraph()
        sig = doc.add_table(rows=2, cols=3)
        sig.style = "Table Grid"
        _set_table_borders(sig)
        for i, (role, key) in enumerate([("Сдал (Подрядчик):", "contractor_name"), ("Принял (Заказчик):", "customer_name")]):
            sig.rows[i].cells[0].text = role
            sig.rows[i].cells[1].text = project_data.get(key, "")
            sig.rows[i].cells[2].text = "____________ М.П."

        return self._save_document(doc, "KS3", project_data.get("code", "PROJ"))

    def generate_tightness_test_act(self, project_data: Dict, test_data: Dict) -> str:
        """
        Акт испытания на герметичность трубопровода.
        ГОСТ 24054-80, СП РК 2.04-103-2013* п.10
        """
        doc = Document()

        title = doc.add_heading("АКТ ИСПЫТАНИЯ ТРУБОПРОВОДА НА ГЕРМЕТИЧНОСТЬ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"Объект: {project_data.get('name', '')}\n"
            f"Подрядчик: {project_data.get('contractor_name', '')}\n"
            f"Заказчик: {project_data.get('customer_name', '')}\n"
            f"Дата испытания: {test_data.get('test_date', datetime.now().strftime('%d.%m.%Y'))}"
        )

        doc.add_paragraph()
        doc.add_heading("Характеристики испытуемого участка:", level=2)
        params = doc.add_table(rows=6, cols=2)
        params.style = "Table Grid"
        _set_table_borders(params)
        for i, (lbl, val) in enumerate([
            ("Участок (ПК):", test_data.get("section_chainage", "")),
            ("Длина участка:", f"{test_data.get('length_m', '')} м"),
            ("Диаметр:", f"DN{project_data.get('diameter_mm', '')} мм"),
            ("Испытательная среда:", test_data.get("test_medium", "природный газ / воздух")),
            ("Рабочее давление:", f"{project_data.get('working_pressure_mpa', '')} МПа"),
            ("Испытательное давление:", f"{test_data.get('test_pressure_mpa', '')} МПа"),
        ]):
            params.rows[i].cells[0].text = lbl
            params.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            params.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Результаты испытания:", level=2)
        results = doc.add_table(rows=4, cols=2)
        results.style = "Table Grid"
        _set_table_borders(results)
        for i, (lbl, val) in enumerate([
            ("Давление в начале испытания:", f"{test_data.get('pressure_start', '')} МПа"),
            ("Давление в конце испытания:", f"{test_data.get('pressure_end', '')} МПа"),
            ("Продолжительность выдержки:", f"{test_data.get('duration_hours', 24)} часов"),
            ("Результат:", test_data.get("result", "УДОВЛЕТВОРИТЕЛЬНО — утечек не обнаружено")),
        ]):
            results.rows[i].cells[0].text = lbl
            results.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_paragraph(
            "ЗАКЛЮЧЕНИЕ: Трубопровод испытан на герметичность в соответствии с требованиями "
            "ГОСТ 24054-80 и СП РК 2.04-103-2013*. Утечек и дефектов не обнаружено. "
            "Трубопровод считается выдержавшим испытание на герметичность."
        )
        doc.add_paragraph("Нормативные документы: ГОСТ 24054-80, СП РК 2.04-103-2013* п.10")
        doc.add_paragraph()

        sig = doc.add_table(rows=2, cols=3)
        sig.style = "Table Grid"
        _set_table_borders(sig)
        sig.rows[0].cells[0].text = "Производитель работ:"
        sig.rows[0].cells[1].text = test_data.get("foreman", "")
        sig.rows[0].cells[2].text = "____________"
        sig.rows[1].cells[0].text = "Технический надзор:"
        sig.rows[1].cells[1].text = project_data.get("technical_supervisor", "")
        sig.rows[1].cells[2].text = "____________"

        return self._save_document(doc, "TightnessTest", project_data.get("code", "PROJ"))

    def generate_pneumatic_test_act(self, project_data: Dict, test_data: Dict) -> str:
        """
        Акт пневматических испытаний трубопровода.
        ГОСТ 24054-80, СНиП 3.05.02-88*, СП РК 2.04-103-2013*
        """
        doc = Document()

        title = doc.add_heading("АКТ ПНЕВМАТИЧЕСКОГО ИСПЫТАНИЯ ТРУБОПРОВОДА", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"Объект: {project_data.get('name', '')}\n"
            f"Подрядчик: {project_data.get('contractor_name', '')}\n"
            f"Заказчик: {project_data.get('customer_name', '')}\n"
            f"Дата испытания: {test_data.get('test_date', datetime.now().strftime('%d.%m.%Y'))}"
        )

        doc.add_paragraph()
        doc.add_heading("Характеристики испытуемого участка:", level=2)
        params = doc.add_table(rows=7, cols=2)
        params.style = "Table Grid"
        _set_table_borders(params)
        for i, (lbl, val) in enumerate([
            ("Участок (ПК):", test_data.get("section_chainage", "")),
            ("Длина участка:", f"{test_data.get('length_m', '')} м"),
            ("Диаметр:", f"DN{project_data.get('diameter_mm', '')} мм"),
            ("Испытательная среда:", "воздух / инертный газ"),
            ("Рабочее давление:", f"{project_data.get('working_pressure_mpa', '')} МПа"),
            ("Испытательное давление (прочность):", f"{test_data.get('strength_pressure_mpa', '')} МПа"),
            ("Испытательное давление (герметичность):", f"{test_data.get('tightness_pressure_mpa', '')} МПа"),
        ]):
            params.rows[i].cells[0].text = lbl
            params.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            params.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Результаты испытания на прочность:", level=2)
        r1 = doc.add_table(rows=3, cols=2)
        r1.style = "Table Grid"
        _set_table_borders(r1)
        for i, (lbl, val) in enumerate([
            ("Давление в начале выдержки:", f"{test_data.get('strength_p_start', '')} МПа"),
            ("Давление в конце выдержки:", f"{test_data.get('strength_p_end', '')} МПа"),
            ("Выдержка:", f"{test_data.get('strength_hours', 24)} ч — {test_data.get('strength_result', 'УДОВЛЕТВОРИТЕЛЬНО')}"),
        ]):
            r1.rows[i].cells[0].text = lbl
            r1.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Результаты испытания на герметичность:", level=2)
        r2 = doc.add_table(rows=3, cols=2)
        r2.style = "Table Grid"
        _set_table_borders(r2)
        for i, (lbl, val) in enumerate([
            ("Давление в начале выдержки:", f"{test_data.get('tightness_p_start', '')} МПа"),
            ("Давление в конце выдержки:", f"{test_data.get('tightness_p_end', '')} МПа"),
            ("Выдержка:", f"{test_data.get('tightness_hours', 12)} ч — {test_data.get('tightness_result', 'УДОВЛЕТВОРИТЕЛЬНО')}"),
        ]):
            r2.rows[i].cells[0].text = lbl
            r2.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_paragraph(
            "ЗАКЛЮЧЕНИЕ: Трубопровод прошёл пневматические испытания на прочность и герметичность "
            "в соответствии с ГОСТ 24054-80 и СП РК 2.04-103-2013*. "
            "Видимых дефектов и утечек не обнаружено. "
            "Трубопровод считается выдержавшим пневматические испытания."
        )
        doc.add_paragraph("Нормативные документы: ГОСТ 24054-80, СНиП 3.05.02-88*, СП РК 2.04-103-2013*")
        doc.add_paragraph()

        sig = doc.add_table(rows=2, cols=3)
        sig.style = "Table Grid"
        _set_table_borders(sig)
        sig.rows[0].cells[0].text = "Производитель работ:"
        sig.rows[0].cells[1].text = test_data.get("foreman", "")
        sig.rows[0].cells[2].text = "____________"
        sig.rows[1].cells[0].text = "Технический надзор:"
        sig.rows[1].cells[1].text = project_data.get("technical_supervisor", "")
        sig.rows[1].cells[2].text = "____________"

        return self._save_document(doc, "PneumaticTest", project_data.get("code", "PROJ"))

    def generate_intermediate_acceptance_act(self, project_data: Dict, act_data: Dict) -> str:
        """
        Акт промежуточной приёмки ответственных конструкций.
        СНиП РК 3.01.01-2008*, СП РК 1.04.02-2019
        """
        doc = Document()

        title = doc.add_heading(
            "АКТ ПРОМЕЖУТОЧНОЙ ПРИЁМКИ ОТВЕТСТВЕННЫХ КОНСТРУКЦИЙ", 0
        )
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(
            f"(СНиП РК 3.01.01-2008* п.8.7, СП РК 1.04.02-2019)"
        ).alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"г. {project_data.get('region', '')}    «___» _________ {datetime.now().year} г."
        )

        doc.add_paragraph()
        doc.add_heading("Данные о конструкции:", level=2)
        info = doc.add_table(rows=6, cols=2)
        info.style = "Table Grid"
        _set_table_borders(info)
        for i, (lbl, val) in enumerate([
            ("Объект:", project_data.get("name", "")),
            ("Наименование конструкции:", act_data.get("structure_name", "")),
            ("Участок (ПК):", act_data.get("chainage", "")),
            ("Нормативный документ:", act_data.get("normative", "СНиП РК")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Заказчик:", project_data.get("customer_name", "")),
        ]):
            info.rows[i].cells[0].text = lbl
            info.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            info.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_paragraph(
            f"Настоящий акт составлен в том, что подрядная организация "
            f"«{project_data.get('contractor_name', '')}» выполнила "
            f"«{act_data.get('structure_name', 'конструкции')}» в объёме "
            f"«{act_data.get('scope', '')}» в соответствии с проектной документацией "
            f"и требованиями нормативных документов."
        )

        doc.add_paragraph()
        doc.add_paragraph(
            "На основании проведённой проверки и освидетельствования: "
            "конструкции признаются ПРИНЯТЫМИ и разрешается продолжение строительства."
        ).runs[0].bold = True

        doc.add_paragraph()
        doc.add_paragraph("Прилагаемая исполнительная документация:")
        for item in act_data.get("attached_docs", ["Исполнительная схема", "Лабораторные заключения", "Сертификаты материалов"]):
            p = doc.add_paragraph(f"— {item}")
            p.paragraph_format.left_indent = Cm(1)

        doc.add_paragraph()
        sig = doc.add_table(rows=3, cols=3)
        sig.style = "Table Grid"
        _set_table_borders(sig)
        sig.rows[0].cells[0].text = "Производитель работ (подрядчик):"
        sig.rows[0].cells[2].text = "____________"
        sig.rows[1].cells[0].text = "Авторский надзор (проектировщик):"
        sig.rows[1].cells[2].text = "____________"
        sig.rows[2].cells[0].text = "Технический надзор (заказчик):"
        sig.rows[2].cells[2].text = "____________"

        return self._save_document(doc, "IntermediateAcceptance", project_data.get("code", "PROJ"))

    def generate_welding_journal(self, project_data: Dict, entries: List = None) -> str:
        """
        Журнал производства сварочных работ.
        ВСН 012-88, РД РК 3.01.001-2019
        """
        doc = Document()
        section = doc.sections[0]
        section.page_width  = Cm(29.7)
        section.page_height = Cm(21.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.0)

        title = doc.add_heading("ЖУРНАЛ ПРОИЗВОДСТВА СВАРОЧНЫХ РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("(ВСН 012-88 ч.I, РД РК 3.01.001-2019)").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        info_tbl = doc.add_table(rows=6, cols=2)
        info_tbl.style = "Table Grid"
        _set_table_borders(info_tbl)
        for i, (lbl, val) in enumerate([
            ("Наименование объекта:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Диаметр / Марка стали:", f"DN{project_data.get('diameter_mm', '—')} мм"),
            ("Нормативный документ:", "ВСН 012-88, РД РК 3.01.001-2019"),
        ]):
            r = info_tbl.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val) if val else "—"

        doc.add_paragraph()

        # Основная таблица стыков
        tbl = doc.add_table(rows=1, cols=11)
        tbl.style = "Table Grid"
        _set_table_borders(tbl)
        headers = [
            "№ п/п", "Дата", "№ стыка", "ПК (пикет)", "Ø трубы, мм",
            "Толщ. стенки, мм", "Клеймо сварщика", "Метод сварки",
            "Вид НК", "Результат НК", "Примечание",
        ]
        hrow = tbl.rows[0]
        for j, h in enumerate(headers):
            hrow.cells[j].text = h
            hrow.cells[j].paragraphs[0].runs[0].bold = True
            hrow.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for idx, e in enumerate(entries or [], 1):
            row = tbl.add_row()
            row.cells[0].text  = str(idx)
            row.cells[1].text  = e.get("date", "")
            row.cells[2].text  = e.get("joint_number", "")
            row.cells[3].text  = e.get("chainage", "")
            row.cells[4].text  = str(project_data.get("diameter_mm", ""))
            row.cells[5].text  = e.get("wall_thickness_mm", "")
            row.cells[6].text  = e.get("welder_stamp", "")
            row.cells[7].text  = e.get("weld_method", "РАД")
            row.cells[8].text  = e.get("ndt_type", "ВИК+УЗК")
            row.cells[9].text  = e.get("ndt_result", "Удовл.")
            row.cells[10].text = e.get("note", "")

        if not entries:
            tbl.add_row()

        doc.add_paragraph()
        doc.add_paragraph("Производитель работ: _________________ / _________________ / «___» ________ ___ г.")

        return self._save_document(doc, "WeldingJournal", project_data.get("code", "PROJ"))

    def generate_ks2(self, project_data: Dict, ks2_data: Dict) -> str:
        """
        Акт о приёмке выполненных работ (КС-2).
        Форма утверждена приказом МФ РК.
        """
        doc = Document()

        title = doc.add_heading("АКТ О ПРИЁМКЕ ВЫПОЛНЕННЫХ РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub = doc.add_paragraph("(Форма КС-2)")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"г. {project_data.get('region', '')}    «___» _________ {datetime.now().year} г."
        )
        doc.add_paragraph()

        # Реквизиты
        req_tbl = doc.add_table(rows=6, cols=2)
        req_tbl.style = "Table Grid"
        _set_table_borders(req_tbl)
        for i, (lbl, val) in enumerate([
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Объект:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Отчётный период:", ks2_data.get("period", "________________")),
            ("Номер договора подряда:", ks2_data.get("contract_number", "_______________")),
        ]):
            r = req_tbl.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Перечень выполненных работ:", level=2)

        works = ks2_data.get("works", [])
        work_tbl = doc.add_table(rows=1, cols=7)
        work_tbl.style = "Table Grid"
        _set_table_borders(work_tbl)
        whdr = work_tbl.rows[0]
        for j, h in enumerate(["№", "Наименование работ", "Ед. изм.", "Кол-во по смете", "Выполнено", "Цена за ед., тг.", "Сумма, тг."]):
            whdr.cells[j].text = h
            whdr.cells[j].paragraphs[0].runs[0].bold = True
            whdr.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        total = 0.0
        for idx, w in enumerate(works, 1):
            qty    = float(w.get("quantity", 0) or 0)
            price  = float(w.get("unit_price", 0) or 0)
            amount = qty * price
            total += amount
            row = work_tbl.add_row()
            row.cells[0].text = str(idx)
            row.cells[1].text = w.get("name", "")
            row.cells[2].text = w.get("unit", "")
            row.cells[3].text = str(w.get("planned_qty", ""))
            row.cells[4].text = str(qty)
            row.cells[5].text = f"{price:,.2f}"
            row.cells[6].text = f"{amount:,.2f}"

        if not works:
            work_tbl.add_row()
            total_row = work_tbl.add_row()
        else:
            total_row = work_tbl.add_row()

        total_row.cells[5].text = "ИТОГО:"
        total_row.cells[5].paragraphs[0].runs[0].bold = True
        total_row.cells[6].text = f"{total:,.2f} тг."
        total_row.cells[6].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()
        doc.add_paragraph(
            f"Итого по акту: {ks2_data.get('total_amount', _number_to_words(total))} тенге."
        ).runs[0].bold = True

        doc.add_paragraph()
        doc.add_paragraph(
            "Работы выполнены в соответствии с проектной документацией, "
            "требованиями нормативно-технических документов РК и условиями договора."
        )

        doc.add_paragraph()
        sig_tbl = doc.add_table(rows=2, cols=3)
        sig_tbl.style = "Table Grid"
        _set_table_borders(sig_tbl)
        for i, (role, name_key) in enumerate([
            ("Сдал (Подрядчик):", "contractor_name"),
            ("Принял (Заказчик):", "customer_name"),
        ]):
            sig_tbl.rows[i].cells[0].text = role
            sig_tbl.rows[i].cells[1].text = project_data.get(name_key, "")
            sig_tbl.rows[i].cells[2].text = "____________ М.П."

        return self._save_document(doc, "KS2", project_data.get("code", "PROJ"))

    def generate_ks2_full(self, project_data: Dict, ks2_data: Dict) -> str:
        """
        КС-2 «Акт о приёмке выполненных работ» с накопительными итогами.
        Столбцы: №пп | Код НТД | Наименование | Ед | Объём по смете |
                  Выполнено за период | Нарастающим итогом | Цена | Сумма за период | Сумма нарастающим
        Форма строго соответствует Приказу МФ РК о первичных учётных документах.
        """
        doc = Document()
        section = doc.sections[0]
        section.page_width  = Cm(42.0)   # A3 альбомная
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.0)
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)

        # ── Шапка ────────────────────────────────────────────────────────────
        title = doc.add_heading("АКТ О ПРИЁМКЕ ВЫПОЛНЕННЫХ РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub = doc.add_paragraph("(Форма КС-2)")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"г. {project_data.get('region', '')}    «___» _________ {datetime.now().year} г."
        )
        doc.add_paragraph()

        # Реквизиты
        req = doc.add_table(rows=7, cols=2)
        req.style = "Table Grid"
        _set_table_borders(req)
        for i, (lbl, val) in enumerate([
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Объект:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Номер акта:", ks2_data.get("act_number", "___")),
            ("Отчётный период:", ks2_data.get("period", "___")),
            ("Номер договора подряда:", ks2_data.get("contract_number", "___")),
        ]):
            r = req.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Перечень выполненных работ:", level=2)

        # ── Таблица работ ────────────────────────────────────────────────────
        COLS = ["№\nпп", "Код\nНТД", "Наименование\nработ и затрат", "Ед.\nизм.",
                "Объём\nпо смете", "Выполнено\nза период", "Нарастающим\nитогом",
                "Цена за ед.,\nтг.", "Сумма\nза период, тг.", "Сумма\nнараст., тг."]
        tbl = doc.add_table(rows=1, cols=len(COLS))
        tbl.style = "Table Grid"
        _set_table_borders(tbl)
        for j, h in enumerate(COLS):
            cell = tbl.rows[0].cells[j]
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        works = ks2_data.get("works", [])
        total_period = 0.0
        total_cumul  = 0.0
        current_section = None

        for idx, w in enumerate(works, 1):
            # Заголовок раздела
            sec = w.get("section", "")
            if sec and sec != current_section:
                current_section = sec
                sec_row = tbl.add_row()
                sec_cell = sec_row.cells[0]
                sec_cell.merge(sec_row.cells[len(COLS) - 1])
                sec_cell.text = sec
                sec_cell.paragraphs[0].runs[0].bold = True
                sec_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            qty     = float(w.get("quantity", 0) or 0)
            c_qty   = float(w.get("cumulative_qty", 0) or 0)
            price   = float(w.get("unit_price", 0) or 0)
            amount  = float(w.get("amount", qty * price))
            c_amount = float(w.get("cumulative_amount", c_qty * price))
            total_period += amount
            total_cumul  += c_amount

            row = tbl.add_row()
            row.cells[0].text = str(w.get("position_no", idx))
            row.cells[1].text = w.get("normative_code", "")
            row.cells[2].text = w.get("name", "")
            row.cells[3].text = w.get("unit", "")
            row.cells[4].text = f"{w.get('planned_qty', 0):g}"
            row.cells[5].text = f"{qty:g}"
            row.cells[6].text = f"{c_qty:g}"
            row.cells[7].text = f"{price:,.2f}"
            row.cells[8].text = f"{amount:,.2f}"
            row.cells[9].text = f"{c_amount:,.2f}"
            # Маршрут/ПК в примечание (ячейка наименования)
            chainages = w.get("chainages", "")
            if chainages:
                row.cells[2].paragraphs[0].add_run(f"\n  ({chainages})").font.size = Pt(7)

        # Итого
        total_row = tbl.add_row()
        total_row.cells[1].merge(total_row.cells[7])
        total_row.cells[1].text = "ИТОГО:"
        total_row.cells[1].paragraphs[0].runs[0].bold = True
        total_row.cells[8].text = f"{total_period:,.2f}"
        total_row.cells[8].paragraphs[0].runs[0].bold = True
        total_row.cells[9].text = f"{total_cumul:,.2f}"
        total_row.cells[9].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()
        nds = total_period * 0.12
        total_with_nds = total_period + nds
        doc.add_paragraph(
            f"Итого по акту за отчётный период: {total_period:,.2f} тг.\n"
            f"НДС 12%: {nds:,.2f} тг.\n"
            f"Итого с НДС: {total_with_nds:,.2f} тг."
        ).runs[0].bold = True

        doc.add_paragraph()
        doc.add_paragraph(
            "Работы выполнены в соответствии с проектной документацией, "
            "нормативными требованиями РК и условиями договора подряда."
        )

        doc.add_paragraph()
        sig = doc.add_table(rows=2, cols=4)
        sig.style = "Table Grid"
        _set_table_borders(sig)
        for i, (role, name_key) in enumerate([
            ("Сдал (Подрядчик):", "contractor_name"),
            ("Принял (Заказчик / тех. надзор):", "customer_name"),
        ]):
            sig.rows[i].cells[0].text = role
            sig.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            sig.rows[i].cells[1].text = project_data.get(name_key, "")
            sig.rows[i].cells[2].text = "____________"
            sig.rows[i].cells[3].text = "М.П."

        return self._save_document(doc, "KS2_Full", project_data.get("code", "PROJ"))

    def generate_ks3_from_ks2(self, project_data: Dict, ks3_data: Dict) -> str:
        """
        КС-3 «Справка о стоимости выполненных работ и затрат» — формируется на основе
        итогов КС-2. Содержит: нарастающий итог, итог за период, НДС 12%.
        """
        doc = Document()

        title = doc.add_heading("СПРАВКА О СТОИМОСТИ ВЫПОЛНЕННЫХ РАБОТ И ЗАТРАТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub = doc.add_paragraph("(Форма КС-3)")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"г. {project_data.get('region', '')}    «___» _________ {datetime.now().year} г."
        )
        doc.add_paragraph()

        # Реквизиты
        req = doc.add_table(rows=5, cols=2)
        req.style = "Table Grid"
        _set_table_borders(req)
        for i, (lbl, val) in enumerate([
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Подрядчик:", project_data.get("contractor_name", "")),
            ("Объект:", project_data.get("name", "")),
            ("Отчётный период:", ks3_data.get("period", "___")),
            ("Номер договора подряда:", ks3_data.get("contract_number", "___")),
        ]):
            r = req.rows[i]
            r.cells[0].text = lbl
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Стоимость выполненных работ:", level=2)

        # Таблица КС-3
        tbl = doc.add_table(rows=1, cols=5)
        tbl.style = "Table Grid"
        _set_table_borders(tbl)
        for j, h in enumerate([
            "№", "Наименование затрат",
            "Сметная стоимость, тг.",
            "Выполнено с начала строительства, тг.",
            "В том числе за отчётный период, тг.",
        ]):
            cell = tbl.rows[0].cells[j]
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        total_period  = float(ks3_data.get("total_period", 0) or 0)
        total_cumul   = float(ks3_data.get("total_cumulative", 0) or 0)
        total_planned = float(ks3_data.get("total_planned", 0) or 0)

        # Строки
        rows_data = [
            ("1", "Строительные и монтажные работы", total_planned, total_cumul, total_period),
        ]
        for pos, name, planned, cumul, period in rows_data:
            row = tbl.add_row()
            row.cells[0].text = str(pos)
            row.cells[1].text = name
            row.cells[2].text = f"{planned:,.2f}"
            row.cells[3].text = f"{cumul:,.2f}"
            row.cells[4].text = f"{period:,.2f}"

        # Итого
        total_row = tbl.add_row()
        for j, val in enumerate(["", "ИТОГО:", f"{total_planned:,.2f}", f"{total_cumul:,.2f}", f"{total_period:,.2f}"]):
            total_row.cells[j].text = val
            if val.startswith("ИТОГО"):
                total_row.cells[j].paragraphs[0].runs[0].bold = True

        nds = total_period * 0.12
        nds_cumul = total_cumul * 0.12

        # НДС строка
        nds_row = tbl.add_row()
        nds_row.cells[1].text = "НДС (12%):"
        nds_row.cells[2].text = ""
        nds_row.cells[3].text = f"{nds_cumul:,.2f}"
        nds_row.cells[4].text = f"{nds:,.2f}"

        # Итого с НДС
        grand_row = tbl.add_row()
        grand_row.cells[1].text = "ИТОГО с НДС:"
        grand_row.cells[1].paragraphs[0].runs[0].bold = True
        grand_row.cells[3].text = f"{total_cumul + nds_cumul:,.2f}"
        grand_row.cells[3].paragraphs[0].runs[0].bold = True
        grand_row.cells[4].text = f"{total_period + nds:,.2f}"
        grand_row.cells[4].paragraphs[0].runs[0].bold = True

        doc.add_paragraph()
        doc.add_paragraph(
            f"Справка составлена на основании Акта КС-2 № {ks3_data.get('act_ref', '___')}."
        )
        doc.add_paragraph(
            f"Итого к оплате за отчётный период (с НДС): {total_period + nds:,.2f} тенге."
        ).runs[0].bold = True

        doc.add_paragraph()
        sig = doc.add_table(rows=2, cols=3)
        sig.style = "Table Grid"
        _set_table_borders(sig)
        for i, (role, name_key) in enumerate([
            ("Сдал (Подрядчик):", "contractor_name"),
            ("Принял (Заказчик):", "customer_name"),
        ]):
            sig.rows[i].cells[0].text = role
            sig.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            sig.rows[i].cells[1].text = project_data.get(name_key, "")
            sig.rows[i].cells[2].text = "____________ М.П."

        return self._save_document(doc, "KS3_Full", project_data.get("code", "PROJ"))

    def generate_purge_act(self, project_data: Dict, purge_data: Dict) -> str:
        """
        Акт продувки и осушки газопровода.
        СП РК 2.04-103-2013* п.10.5
        """
        doc = Document()

        title = doc.add_heading("АКТ ПРОДУВКИ И ОСУШКИ ТРУБОПРОВОДА", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()
        doc.add_paragraph(
            f"Объект: {project_data.get('name', '')}\n"
            f"Шифр: {project_data.get('code', '')}\n"
            f"Дата: {purge_data.get('date', datetime.now().strftime('%d.%m.%Y'))}"
        )

        doc.add_paragraph()
        doc.add_heading("Характеристики участка:", level=2)
        p_tbl = doc.add_table(rows=5, cols=2)
        p_tbl.style = "Table Grid"
        _set_table_borders(p_tbl)
        for i, (lbl, val) in enumerate([
            ("Участок (ПК):", purge_data.get("section_chainage", "")),
            ("Длина участка:", f"{purge_data.get('length_m', '')} м"),
            ("Диаметр:", f"DN{project_data.get('diameter_mm', '')} мм"),
            ("Давление продувки:", f"{purge_data.get('purge_pressure_mpa', '')} МПа"),
            ("Продолжительность:", f"{purge_data.get('duration_min', '')} мин"),
        ]):
            p_tbl.rows[i].cells[0].text = lbl
            p_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
            p_tbl.rows[i].cells[1].text = str(val)

        doc.add_paragraph()
        doc.add_heading("Результаты:", level=2)
        doc.add_paragraph(
            f"Продувочная среда: {purge_data.get('purge_medium', 'сжатый воздух / инертный газ')}\n"
            f"Точка росы после осушки: {purge_data.get('dew_point', '−20')} °C\n"
            f"Результат: {purge_data.get('result', 'Продувка и осушка выполнены. Трубопровод подготовлен к испытаниям.')}"
        )

        doc.add_paragraph()
        doc.add_paragraph("Нормативный документ: СП РК 2.04-103-2013* п.10.5, ВСН 012-88")
        doc.add_paragraph()

        sig2 = doc.add_table(rows=2, cols=3)
        sig2.style = "Table Grid"
        _set_table_borders(sig2)
        sig2.rows[0].cells[0].text = "Производитель работ:"
        sig2.rows[0].cells[1].text = purge_data.get("foreman", "")
        sig2.rows[0].cells[2].text = "____________"
        sig2.rows[1].cells[0].text = "Технический надзор:"
        sig2.rows[1].cells[1].text = project_data.get("technical_supervisor", "")
        sig2.rows[1].cells[2].text = "____________"

        return self._save_document(doc, "PurgeAct", project_data.get("code", "PROJ"))


    # ─── ППР и техкарты ────────────────────────────────────────────────────────

    def generate_ppr(self, project_data: Dict, ppr_options: Dict = None) -> str:
        """
        Проект производства работ (ППР).
        СНиП РК 3.01.01-2008*, СП РК 1.04.02-2019
        """
        from app.models.shift_report import (
            ConstructionPhase, PHASE_NAMES_RU,
            PHASE_NORMATIVES, PHASE_TYPICAL_MACHINERY,
        )

        opts = ppr_options or {}
        method = opts.get("installation_method", "открытая траншея")
        doc = Document()

        section = doc.sections[0]
        section.left_margin  = Cm(2.5)
        section.right_margin = Cm(1.5)
        section.top_margin   = Cm(2.0)
        section.bottom_margin = Cm(2.0)

        # ── Титульный лист ──────────────────────────────────────────────────
        doc.add_paragraph()
        doc.add_paragraph()
        title = doc.add_heading("ПРОЕКТ ПРОИЗВОДСТВА РАБОТ", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub = doc.add_paragraph(f"по строительству объекта:")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub.runs[0].bold = True

        obj_p = doc.add_paragraph(project_data.get("name", ""))
        obj_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        obj_p.runs[0].bold = True
        obj_p.runs[0].font.size = Pt(14)

        doc.add_paragraph(f'Шифр проекта: {project_data.get("code", "")}').alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        sign_tbl = doc.add_table(rows=4, cols=3)
        sign_tbl.style = "Table Grid"
        _set_table_borders(sign_tbl)
        sign_rows = [
            ("Заказчик:", project_data.get("customer_name", "___________________")),
            ("Генеральный подрядчик:", project_data.get("contractor_name", "___________________")),
            ("Главный инженер:", project_data.get("technical_supervisor", "___________________")),
            ("Разработан:", datetime.now().strftime("%d.%m.%Y")),
        ]
        for i, (label, value) in enumerate(sign_rows):
            r = sign_tbl.rows[i]
            r.cells[0].text = label
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = value
            r.cells[2].text = "_________________ (подпись)"

        doc.add_page_break()

        # ── Общие данные ────────────────────────────────────────────────────
        doc.add_heading("1. ОБЩИЕ ДАННЫЕ ОБ ОБЪЕКТЕ СТРОИТЕЛЬСТВА", level=1)

        obj_table = doc.add_table(rows=9, cols=2)
        obj_table.style = "Table Grid"
        _set_table_borders(obj_table)
        obj_fields = [
            ("Наименование объекта:", project_data.get("name", "")),
            ("Шифр проекта:", project_data.get("code", "")),
            ("Тип объекта:", project_data.get("project_type", "")),
            ("Заказчик:", project_data.get("customer_name", "")),
            ("Генеральный подрядчик:", project_data.get("contractor_name", "")),
            ("Проектная организация:", project_data.get("designer_name", "")),
            ("Регион:", project_data.get("region", "")),
            ("Протяжённость:", f"{project_data.get('total_length_km', '')} км"),
            ("Диаметр / давление:", f"DN{project_data.get('diameter_mm', '')} / {project_data.get('working_pressure_mpa', '')} МПа"),
        ]
        for i, (label, value) in enumerate(obj_fields):
            r = obj_table.rows[i]
            r.cells[0].text = label
            r.cells[0].paragraphs[0].runs[0].bold = True
            r.cells[1].text = str(value) if value else "—"

        doc.add_paragraph()
        doc.add_heading("1.1 Метод производства основных работ", level=2)
        doc.add_paragraph(f"Способ прокладки трубопровода: {method}.")
        doc.add_paragraph(
            "Все работы выполняются в соответствии с требованиями СП РК 2.04-103-2013*, "
            "СНиП РК 3.01.01-2008*, ВСН 012-88 и настоящим ППР."
        )

        # ── Организация производства ────────────────────────────────────────
        doc.add_heading("2. ОРГАНИЗАЦИЯ СТРОИТЕЛЬНОГО ПРОИЗВОДСТВА", level=1)
        doc.add_paragraph(
            "Строительно-монтажные работы выполняются поточным методом. "
            "Весь фронт работ разбивается на захватки длиной 2–5 км. "
            "На каждой захватке одновременно работают специализированные бригады "
            "по технологическим фазам."
        )

        doc.add_heading("2.1 Технологическая последовательность работ", level=2)
        seq_table = doc.add_table(rows=1, cols=3)
        seq_table.style = "Table Grid"
        _set_table_borders(seq_table)
        hdr = seq_table.rows[0]
        for j, h in enumerate(["№", "Наименование вида работ", "Нормативный документ"]):
            hdr.cells[j].text = h
            hdr.cells[j].paragraphs[0].runs[0].bold = True

        for i, phase in enumerate(ConstructionPhase, 1):
            row = seq_table.add_row()
            row.cells[0].text = str(i)
            row.cells[1].text = PHASE_NAMES_RU[phase]
            row.cells[2].text = ", ".join(PHASE_NORMATIVES.get(phase, []))

        # ── Машины и механизмы ──────────────────────────────────────────────
        doc.add_heading("3. СОСТАВ МАШИН И МЕХАНИЗМОВ", level=1)
        doc.add_paragraph(
            "Состав механизированной колонны принимается в соответствии с "
            "технологическими картами и объёмами работ."
        )

        mech_table = doc.add_table(rows=1, cols=3)
        mech_table.style = "Table Grid"
        _set_table_borders(mech_table)
        mhdr = mech_table.rows[0]
        for j, h in enumerate(["Фаза работ", "Машины и механизмы", "Количество"]):
            mhdr.cells[j].text = h
            mhdr.cells[j].paragraphs[0].runs[0].bold = True

        for phase in ConstructionPhase:
            machines = PHASE_TYPICAL_MACHINERY.get(phase, [])
            if not machines:
                continue
            row = mech_table.add_row()
            row.cells[0].text = PHASE_NAMES_RU[phase]
            row.cells[1].text = "\n".join(f"• {m}" for m in machines)
            row.cells[2].text = "По ПОС"

        # ── Охрана труда ────────────────────────────────────────────────────
        doc.add_heading("4. ТРЕБОВАНИЯ ОХРАНЫ ТРУДА И ПРОМЫШЛЕННОЙ БЕЗОПАСНОСТИ", level=1)
        ot_items = [
            "Все работники должны иметь действующие удостоверения по профессии и ОТ.",
            "Работы в охранной зоне трубопроводов выполнять только при наличии наряда-допуска.",
            "При производстве земляных работ на глубине более 1,5 м — обязательное крепление стенок траншеи.",
            "Сварочные работы — огневые работы, выполняются по наряду-допуску.",
            "Подъёмно-транспортные работы — только аттестованными стропальщиками и крановщиками.",
            "Испытание трубопровода — по специальной программе с выставлением охраны в зоне опасности.",
            "Газоопасные работы при пуске газа — по наряду-допуску, с применением СИЗ органов дыхания.",
            "Обязательное использование СИЗ: каски, жилеты, спецодежда, спецобувь.",
        ]
        for item in ot_items:
            doc.add_paragraph(item, style="List Bullet")

        doc.add_paragraph()
        doc.add_paragraph(
            "Нормативные документы: ГОСТ 12.0.004-2015, ГОСТ 12.3.016-87, "
            "Закон РК «О безопасности и охране труда», Правила ПБ при строительстве МГ."
        )

        # ── ООС ─────────────────────────────────────────────────────────────
        doc.add_heading("5. ОХРАНА ОКРУЖАЮЩЕЙ СРЕДЫ", level=1)
        oos_items = [
            "Снятие и складирование плодородного слоя почвы с последующей рекультивацией.",
            "Запрет на слив ГСМ и сточных вод вне специально отведённых мест.",
            "Трасса трубопровода после укладки засыпается с восстановлением рельефа.",
            "Рекультивация нарушенных угодий в соответствии с проектом.",
            "Переходы через водные преграды — по специальным методам (ГНБ/НБ).",
        ]
        for item in oos_items:
            doc.add_paragraph(item, style="List Bullet")

        # ── Перечень техкарт ─────────────────────────────────────────────────
        doc.add_heading("6. ПЕРЕЧЕНЬ ТЕХНОЛОГИЧЕСКИХ КАРТ (ПРИЛОЖЕНИЯ)", level=1)
        tc_table = doc.add_table(rows=1, cols=2)
        tc_table.style = "Table Grid"
        _set_table_borders(tc_table)
        tc_hdr = tc_table.rows[0]
        tc_hdr.cells[0].text = "Приложение"
        tc_hdr.cells[0].paragraphs[0].runs[0].bold = True
        tc_hdr.cells[1].text = "Наименование технологической карты"
        tc_hdr.cells[1].paragraphs[0].runs[0].bold = True

        for i, phase in enumerate(ConstructionPhase, 1):
            row = tc_table.add_row()
            row.cells[0].text = f"ТК-{i:02d}"
            row.cells[1].text = PHASE_NAMES_RU[phase]

        return self._save_document(doc, "PPR", project_data.get("code", "PROJ"))

    def generate_tech_card(
        self,
        project_data: Dict,
        phase_value: str,
        card_number: int = 1,
        custom_scope: str = "",
    ) -> str:
        """
        Технологическая карта на конкретный вид работ.
        СНиП РК 3.01.01-2008*
        """
        from app.models.shift_report import (
            ConstructionPhase, PHASE_NAMES_RU,
            PHASE_NORMATIVES, PHASE_TYPICAL_MACHINERY,
        )

        try:
            phase = ConstructionPhase(phase_value)
        except ValueError:
            phase = ConstructionPhase.TRENCH_EXCAVATION

        phase_name = PHASE_NAMES_RU[phase]
        normatives = PHASE_NORMATIVES.get(phase, [])
        machinery  = PHASE_TYPICAL_MACHINERY.get(phase, [])

        # Загружаем справочные данные
        _ensure_data()

        # Типовые операции по фазе
        PHASE_OPERATIONS = _TECH_CARD_OPERATIONS.get(phase, [
            ("Подготовительные работы", "Проверка технического состояния машин и механизмов, инструктаж персонала"),
            ("Основные работы", f"Производство работ по фазе: {phase_name}"),
            ("Контроль качества", "Операционный и визуальный контроль в соответствии с НТД"),
            ("Сдача-приёмка", "Оформление актов и разрешение на последующие работы"),
        ])

        doc = Document()
        section = doc.sections[0]
        section.left_margin  = Cm(2.5)
        section.right_margin = Cm(1.5)

        # ── Заголовок ───────────────────────────────────────────────────────
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.add_run(f"Приложение ТК-{card_number:02d} к ППР").italic = True

        title = doc.add_heading("ТЕХНОЛОГИЧЕСКАЯ КАРТА", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub = doc.add_paragraph(phase_name.upper())
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub.runs[0].bold = True
        sub.runs[0].font.size = Pt(13)

        doc.add_paragraph(
            f"Объект: {project_data.get('name', '')}    Шифр: {project_data.get('code', '')}"
        ).alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()

        # ── 1. Назначение ────────────────────────────────────────────────────
        doc.add_heading("1. НАЗНАЧЕНИЕ И ОБЛАСТЬ ПРИМЕНЕНИЯ", level=1)
        doc.add_paragraph(
            f"Настоящая технологическая карта предназначена для выполнения работ: "
            f"«{phase_name}» при строительстве объекта «{project_data.get('name', '')}»."
        )
        if custom_scope:
            doc.add_paragraph(f"Особые условия: {custom_scope}")
        doc.add_paragraph(
            f"Объект: трубопровод DN{project_data.get('diameter_mm', '—')} мм, "
            f"Р={project_data.get('working_pressure_mpa', '—')} МПа, "
            f"L={project_data.get('total_length_km', '—')} км."
        )

        # ── 2. Предшествующие работы ─────────────────────────────────────────
        doc.add_heading("2. ТРЕБОВАНИЯ К ПРЕДШЕСТВУЮЩИМ РАБОТАМ", level=1)
        prev_work = _PRECEDING_WORKS.get(phase, "Предшествующие работы должны быть выполнены в полном объёме и приняты по актам.")
        doc.add_paragraph(prev_work)

        # ── 3. Персонал ──────────────────────────────────────────────────────
        doc.add_heading("3. СОСТАВ ИСПОЛНИТЕЛЕЙ", level=1)
        staff_table = doc.add_table(rows=1, cols=3)
        staff_table.style = "Table Grid"
        _set_table_borders(staff_table)
        sh = staff_table.rows[0]
        for j, h in enumerate(["Должность / профессия", "Разряд / категория", "Количество, чел."]):
            sh.cells[j].text = h
            sh.cells[j].paragraphs[0].runs[0].bold = True
        for pos, grade, qty in _STAFF.get(phase, [("Рабочие", "4–5", "По ПОС"), ("ИТР", "—", "1")]):
            r = staff_table.add_row()
            r.cells[0].text = pos
            r.cells[1].text = grade
            r.cells[2].text = qty

        # ── 4. Машины и механизмы ────────────────────────────────────────────
        doc.add_heading("4. МАШИНЫ, МЕХАНИЗМЫ И ИНСТРУМЕНТ", level=1)
        if machinery:
            mech_table = doc.add_table(rows=1, cols=3)
            mech_table.style = "Table Grid"
            _set_table_borders(mech_table)
            mhdr = mech_table.rows[0]
            for j, h in enumerate(["Наименование", "Марка / тип", "Количество"]):
                mhdr.cells[j].text = h
                mhdr.cells[j].paragraphs[0].runs[0].bold = True
            for m in machinery:
                row = mech_table.add_row()
                row.cells[0].text = m
                row.cells[1].text = "По ПОС / факт."
                row.cells[2].text = "1"
        else:
            doc.add_paragraph("Ручной инструмент и измерительные приборы по перечню ПОС.")

        # ── 5. Технологическая последовательность ────────────────────────────
        doc.add_heading("5. ТЕХНОЛОГИЧЕСКАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ОПЕРАЦИЙ", level=1)
        ops_table = doc.add_table(rows=1, cols=3)
        ops_table.style = "Table Grid"
        _set_table_borders(ops_table)
        oh = ops_table.rows[0]
        for j, h in enumerate(["№ п/п", "Наименование операции", "Указания по выполнению"]):
            oh.cells[j].text = h
            oh.cells[j].paragraphs[0].runs[0].bold = True
        for i, (op_name, op_desc) in enumerate(PHASE_OPERATIONS, 1):
            row = ops_table.add_row()
            row.cells[0].text = str(i)
            row.cells[1].text = op_name
            row.cells[2].text = op_desc

        # ── 6. Контроль качества ─────────────────────────────────────────────
        doc.add_heading("6. КОНТРОЛЬ КАЧЕСТВА", level=1)
        qc_table = doc.add_table(rows=1, cols=4)
        qc_table.style = "Table Grid"
        _set_table_borders(qc_table)
        qhdr = qc_table.rows[0]
        for j, h in enumerate(["Вид контроля", "Контролируемый параметр", "Метод", "Периодичность"]):
            qhdr.cells[j].text = h
            qhdr.cells[j].paragraphs[0].runs[0].bold = True
        for row_data in _QC_CHECKS.get(phase, [
            ("Входной",      "Соответствие материалов проекту",       "Визуальный, документальный",  "При поступлении"),
            ("Операционный", "Соблюдение технологии производства работ", "Визуальный, инструментальный", "Непрерывно"),
            ("Приёмочный",   "Качество выполненных работ",              "Визуальный, инструментальный", "По завершении"),
        ]):
            row = qc_table.add_row()
            for j, val in enumerate(row_data):
                row.cells[j].text = val

        # ── 7. Охрана труда ──────────────────────────────────────────────────
        doc.add_heading("7. ТРЕБОВАНИЯ ОХРАНЫ ТРУДА И ПБ", level=1)
        for item in _OT_REQUIREMENTS.get(phase, [
            "Инструктаж по ОТ перед началом работ.",
            "Применение СИЗ: каска, жилет, перчатки, спецодежда.",
            "Работы выполнять только в светлое время суток (при отсутствии освещения).",
        ]):
            doc.add_paragraph(item, style="List Bullet")

        # ── 8. Нормативные документы ─────────────────────────────────────────
        doc.add_heading("8. НОРМАТИВНЫЕ ДОКУМЕНТЫ", level=1)
        for norm in normatives:
            doc.add_paragraph(norm, style="List Bullet")
        doc.add_paragraph("СНиП РК 3.01.01-2008* — Организация строительного производства", style="List Bullet")
        doc.add_paragraph("СП РК 1.04.02-2019 — Исполнительная документация", style="List Bullet")
        doc.add_paragraph("ГОСТ 12.0.004-2015 — Инструктажи по ОТ", style="List Bullet")

        # ── Подпись ───────────────────────────────────────────────────────────
        doc.add_paragraph()
        sign2 = doc.add_table(rows=2, cols=3)
        sign2.style = "Table Grid"
        _set_table_borders(sign2)
        sign2.rows[0].cells[0].text = "Разработал:"
        sign2.rows[0].cells[1].text = project_data.get("technical_supervisor", "___________________")
        sign2.rows[0].cells[2].text = "_________________ (подпись)"
        sign2.rows[1].cells[0].text = "Утвердил (ГИП):"
        sign2.rows[1].cells[1].text = "___________________"
        sign2.rows[1].cells[2].text = "_________________ (подпись)"

        phase_slug = phase.value.replace("_", "-")
        return self._save_document(doc, f"TK_{phase_slug}", project_data.get("code", "PROJ"))


def _number_to_words(amount: float) -> str:
    """Сумма прописью (упрощённо, целые тысячи)."""
    try:
        return f"{amount:,.2f}"
    except Exception:
        return str(amount)


def _month_ru(month: int) -> str:
    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    return months.get(month, "")


# ─── Справочные данные технологических карт (операции / персонал / QC / ОТ) ──

def _lazy_phase_data():
    """Вернуть словари с данными для техкарт (импорт внутри, чтобы избежать циклов)."""
    from app.models.shift_report import ConstructionPhase as P

    ops: dict = {
        P.GEODESY_SURVEY: [
            ("Получение разрешительной документации", "Получить разрешение на геодезическую деятельность и ознакомиться с топосъёмкой"),
            ("Рекогносцировка местности", "Обследование трассы, уточнение положения оси в натуре"),
            ("Разбивка оси трубопровода", "Установка вех / кольев по оси через 50 м, разбивка горизонтальных кривых"),
            ("Разбивка зоны отвода", "Обозначение границ полосы отвода"),
            ("Оформление полевого журнала", "Занесение координат в геодезический журнал, сдача бригадиру"),
        ],
        P.TRENCH_EXCAVATION: [
            ("Разметка траншеи", "Установить шнур / обозначить границы траншеи по оси разбивки"),
            ("Снятие растительного слоя", "Бульдозер снимает ПСП в отвал"),
            ("Разработка грунта экскаватором", "Разработка с выкидкой грунта в одностороннее лежачее боковое отвало не ближе 0,5 м от бровки"),
            ("Зачистка дна траншеи", "Ручная зачистка 10–15 см до проектной отметки"),
            ("Операционный контроль", "Нивелирование дна, проверка уклонов, размеров поперечного профиля"),
        ],
        P.PIPE_WELDING: [
            ("Подготовка торцов труб", "Зачистка кромок, удаление заводской фаски до проектной, замер калибром"),
            ("Входной контроль труб", "Проверка сертификатов, визуальный осмотр, замер геометрии"),
            ("Сборка стыка", "Установка труб в центраторе, проверка смещения кромок (не более 1 мм)"),
            ("Сварка корневого прохода", "Ручная дуговая сварка / автомат (по WPS)"),
            ("Сварка заполняющих проходов", "2–3 прохода согласно WPS"),
            ("Сварка облицовочного прохода", "Финишный шов, зачистка шлака"),
            ("Контроль сварного шва", "ВИК + УЗК/РГК в соответствии с ВСН 012-88"),
        ],
        P.PIPE_INSULATION: [
            ("Подготовка поверхности трубы", "Дробеструйная / пескоструйная очистка до Sa 2½"),
            ("Нанесение праймера", "Нанесение адгезионного слоя валиком / безвоздушным распылением"),
            ("Нанесение изоляционного покрытия", "Изоляционная машина — намотка ленты в 2 слоя / нанесение экструзионного PE"),
            ("Контроль покрытия", "Измерение толщины плёнки, диэлектрический контроль (искровой дефектоскоп), адгезия"),
        ],
        P.PIPE_LAYING: [
            ("Проверка готовности траншеи", "Нивелирование дна, осмотр на отсутствие посторонних предметов"),
            ("Устройство мягкой постели", "Подсыпка мягким грунтом 10–15 см"),
            ("Строповка плети", "Захват трубоукладчиками не ближе 3 м от стыков"),
            ("Опускание трубопровода", "Одновременная работа 3–5 трубоукладчиков, контроль прогиба плети"),
            ("Проверка проектного положения", "Нивелирование верха трубы, осмотр сохранности изоляции"),
        ],
        P.HYDRAULIC_TEST: [
            ("Подготовка к испытанию", "Установка заглушек, манометров, соединение с опрессовочным агрегатом"),
            ("Заполнение водой", "Медленное заполнение снизу-вверх с выпуском воздуха"),
            ("Подъём давления до испытательного", "Плавный подъём до Рисп, скорость не более 0,1 МПа/мин"),
            ("Выдержка под давлением (прочность)", "Выдержка согласно проекту (обычно 24 ч)"),
            ("Снижение и выдержка на герметичность", "Снижение до Ргерм и повторная выдержка"),
            ("Осмотр и оценка результата", "Обход трассы, фиксация падения давления / утечек"),
            ("Сброс давления и откачка воды", "Сброс давления, слив и утилизация воды"),
        ],
        P.TRENCH_BACKFILL: [
            ("Подготовка", "Проверка сохранности изоляции трубопровода, акт на укладку"),
            ("Присыпка мягким грунтом", "Засыпка слоем 20–30 см выше верха трубы мягким грунтом вручную"),
            ("Подбивка пазух", "Послойное уплотнение грунта в пазухах"),
            ("Основная засыпка", "Бульдозер: послойная отсыпка по 30 см с уплотнением"),
            ("Устройство нагорного вала / рекультивация", "Формирование бровки с учётом осадки грунта"),
            ("Операционный контроль", "Контроль плотности грунта (ГОСТ 28514)"),
        ],
    }

    preceding: dict = {
        P.CLEARING: "Геодезическая разбивка оси трубопровода выполнена и принята по акту.",
        P.TOPSOIL_REMOVAL: "Расчистка трассы от кустарника и деревьев выполнена и принята.",
        P.TRENCH_EXCAVATION: "Снятие ПСП выполнено. Геодезическая разбивка бровки траншеи произведена.",
        P.TRENCH_PREPARATION: "Траншея разработана до проектной отметки, принята по акту.",
        P.PIPE_WELDING: "Трубы доставлены на трассу, прошли входной контроль. Сварщики аттестованы.",
        P.PIPE_INSULATION: "Сварные стыки приняты по ВИК/УЗК, оформлены акты.",
        P.PIPE_LAYING: "Траншея готова, постель устроена. Изоляция проверена искровым дефектоскопом.",
        P.TRENCH_BACKFILL: "Трубопровод уложен и принят по акту. Изоляция проверена.",
        P.HYDRAULIC_TEST: "Трубопровод уложен, засыпан, оформлены АОСР на все виды скрытых работ.",
        P.PURGE_DRY: "Гидроиспытание успешно, акт оформлен. Вода откачана.",
        P.ECP_INSTALLATION: "Трубопровод уложен, засыпан. ПСП рекультивирован.",
        P.COMMISSIONING: "Все виды испытаний выполнены. ИТД укомплектована. Акт гидроиспытаний положительный.",
    }

    staff: dict = {
        P.GEODESY_SURVEY: [("Геодезист", "Высшее/среднее техн.", "1"), ("Рабочий-реечник", "2–3", "2")],
        P.TRENCH_EXCAVATION: [("Машинист экскаватора", "5–6", "1"), ("Машинист бульдозера", "5", "1"), ("Рабочий-землекоп", "3", "2")],
        P.PIPE_WELDING: [("Сварщик аттестованный", "5–6 НАКС", "4–6"), ("Дефектоскопист", "II–III уровень", "1"), ("Трубоукладчик", "5–6", "2")],
        P.PIPE_INSULATION: [("Изолировщик", "4–5", "3"), ("Трубоукладчик", "5", "1"), ("Лаборант", "3–4", "1")],
        P.PIPE_LAYING: [("Машинист трубоукладчика", "5–6", "4"), ("Стропальщик", "4–5", "4"), ("Геодезист", "—", "1")],
        P.HYDRAULIC_TEST: [("Машинист насосной станции", "4–5", "2"), ("Слесарь трубопроводчик", "4–5", "2"), ("ИТР-ответственный", "—", "1")],
    }

    qc: dict = {
        P.TRENCH_EXCAVATION: [
            ("Входной",      "Отметка дна траншеи",              "Нивелирование",              "Каждые 50 м"),
            ("Операционный", "Ширина и откосы траншеи",           "Инструментально",            "Каждые 50 м"),
            ("Приёмочный",   "Соответствие проекту (профиль)",    "Нивелирование, АОСР",        "По завершении"),
        ],
        P.PIPE_WELDING: [
            ("Входной",      "Сертификаты труб и расходных материалов", "Документальный",       "При поступлении"),
            ("Операционный", "Подготовка кромок, сборка, режимы сварки", "Визуальный, ВИК",    "Каждый стык"),
            ("Приёмочный",   "100% ВИК + выборочно УЗК/РГК",     "ВИК, УЗК, РГК",             "ВСН 012-88"),
        ],
        P.HYDRAULIC_TEST: [
            ("Операционный", "Давление и время выдержки",         "Манометр кл. 0.25",          "Непрерывно"),
            ("Приёмочный",   "Результат испытания",               "Сравнение нач./конечного P",  "По завершении"),
        ],
    }

    ot: dict = {
        P.TRENCH_EXCAVATION: [
            "Работы в траншее глубиной более 1,5 м — только с креплением стенок.",
            "Бровка траншеи должна быть ограждена на расстоянии 1 м.",
            "Запрещено нахождение людей в зоне работы ковша экскаватора (5 м).",
            "Сигнальный жилет обязателен для всех работников.",
        ],
        P.PIPE_WELDING: [
            "Сварочные работы — огневые работы, выполнять по наряду-допуску.",
            "Сварщик обязан иметь действующее удостоверение НАКС.",
            "Защитный щиток/маска, спецодежда из огнестойкого материала.",
            "В охранной зоне действующих трубопроводов — разрешение в установленном порядке.",
        ],
        P.HYDRAULIC_TEST: [
            "Опасная зона по обе стороны испытываемого участка ограждается на 25 м.",
            "Запрещено находиться в зоне опасности при подъёме давления.",
            "Наблюдение за манометром только дистанционно / через защитное стекло.",
            "Сброс давления — плавный, через специальные вентили.",
        ],
        P.GAS_START: [
            "Газоопасные работы — по наряду-допуску, бригада не менее 2 чел.",
            "Обязательное применение газоанализаторов и СИЗ органов дыхания.",
            "Запрет на использование открытого огня в радиусе 100 м.",
            "Связь с диспетчером каждые 30 минут.",
        ],
    }

    return ops, preceding, staff, qc, ot


# Кэш данных (вычисляется при первом обращении)
_TECH_CARD_OPERATIONS: dict = {}
_PRECEDING_WORKS: dict = {}
_STAFF: dict = {}
_QC_CHECKS: dict = {}
_OT_REQUIREMENTS: dict = {}


def _init_tech_card_data():
    global _TECH_CARD_OPERATIONS, _PRECEDING_WORKS, _STAFF, _QC_CHECKS, _OT_REQUIREMENTS
    if _TECH_CARD_OPERATIONS:
        return
    _TECH_CARD_OPERATIONS, _PRECEDING_WORKS, _STAFF, _QC_CHECKS, _OT_REQUIREMENTS = _lazy_phase_data()


# Вызывается при первом использовании в generate_tech_card
import atexit as _atexit  # noqa


def _ensure_data():
    _init_tech_card_data()


# ─────────────────────────────────────────────────────────────────────────────
# Синглтон генератора
document_generator = DocumentGenerator()
