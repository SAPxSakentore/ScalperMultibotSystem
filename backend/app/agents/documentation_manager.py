"""
Асель Нурланова — Ведущий специалист по исполнительно-технической документации
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.agents.base_agent import BaseAgent


class DocumentationManagerAgent(BaseAgent):
    role = "documentation_manager"
    name_ru = "Нурланова Асель Маратовна"
    name_kz = "Нурланова Әсел Маратқызы"
    position = "Ведущий специалист ИТД / Начальник отдела документации"
    avatar_initials = "АН"

    @property
    def system_prompt(self) -> str:
        return """Ты — Асель Нурланова, ведущий специалист по исполнительно-технической документации (ИТД) в Республике Казахстан с 15-летним опытом.

Твои обязанности:
1. Ведение и контроль полноты ИТД строительного проекта
2. Автоматическая генерация строительных документов
3. Формирование ОЖР, АОСР, исполнительных схем, актов
4. Проверка соответствия ИТД требованиям СП РК 1.04.02-2019
5. Учет сертификатов на материалы, паспортов оборудования
6. Формирование реестра ИТД
7. Подготовка документов к сдаче заказчику

Ты работаешь строго по форматам, установленным в СП РК 1.04.02-2019 и нормативах РК.
При составлении документов используй правильную юридическую формулировку.
Все документы составляй на русском языке с соблюдением делопроизводственных норм РК.
"""

    @property
    def capabilities(self) -> List[str]:
        return [
            "Генерация ОЖР (Общий журнал работ)",
            "Генерация АОСР (Акт освидетельствования скрытых работ)",
            "Формирование реестра ИТД",
            "Генерация актов испытаний",
            "Учет сертификатов и паспортов",
            "Генерация исполнительных схем (описание)",
            "Проверка комплектности ИТД",
            "Генерация КС-11, КС-14",
        ]

    async def generate_ojr_entry(self, project_data: Dict, work_data: Dict) -> str:
        """Сформировать запись в Общем журнале работ."""
        prompt = f"""
Составь запись в Общем журнале работ (ОЖР) по форме СП РК 1.04.02-2019.

Проект: {project_data.get('name')}
Шифр: {project_data.get('code')}
Объект: {project_data.get('description')}

Выполненные работы:
{work_data.get('description', 'Строительно-монтажные работы')}

Дата: {work_data.get('date', datetime.now().strftime('%d.%m.%Y'))}
Участок: {work_data.get('section', 'не указан')}
ПК (пикет): {work_data.get('chainage', 'не указан')}
Производитель работ: {work_data.get('foreman', 'не указан')}
Температура воздуха: {work_data.get('temperature', 'не указана')} °C
Погодные условия: {work_data.get('weather', 'не указаны')}

Составь запись в стандартном формате ОЖР.
"""
        return await self.think(prompt, project_type=project_data.get("project_type"))

    async def generate_aosr(self, project_data: Dict, work_data: Dict) -> Dict:
        """Сформировать Акт освидетельствования скрытых работ (АОСР)."""
        prompt = f"""
Составь Акт освидетельствования скрытых работ (АОСР) в соответствии с СП РК 1.04.02-2019.

ДАННЫЕ ПРОЕКТА:
Наименование объекта: {project_data.get('name')}
Шифр проекта: {project_data.get('code')}
Заказчик: {project_data.get('customer_name')}
Генподрядчик: {project_data.get('contractor_name')}
Проектировщик: {project_data.get('designer_name')}

СКРЫТЫЕ РАБОТЫ:
Наименование работ: {work_data.get('work_name')}
Место выполнения (ПК): {work_data.get('chainage', 'не указан')}
Дата выполнения: {work_data.get('date', datetime.now().strftime('%d.%m.%Y'))}
Применяемые материалы: {work_data.get('materials', 'не указаны')}
Нормативные документы: {work_data.get('normatives', 'СП РК 2.04-103-2013*')}

Составь полный текст АОСР по установленной форме РК, включая:
1. Шапку документа
2. Описание выполненных работ
3. Применяемые материалы и их соответствие проекту
4. Ссылки на нормативные документы
5. Заключение о соответствии работ проекту и НТД
6. Разрешение на производство последующих работ
7. Подписи (Технический надзор, Авторский надзор, Производитель работ)
"""
        result_text = await self.think(prompt, project_type=project_data.get("project_type"))
        return {
            "document_type": "aosr",
            "content_text": result_text,
            "metadata": {
                "project_code": project_data.get("code"),
                "work_name": work_data.get("work_name"),
                "date": work_data.get("date", datetime.now().strftime("%d.%m.%Y")),
                "chainage": work_data.get("chainage"),
            }
        }

    async def check_itd_completeness(self, project_data: Dict, existing_docs: List) -> str:
        """Проверить полноту комплекта ИТД."""
        doc_list = "\n".join([f"- {d}" for d in existing_docs]) if existing_docs else "Документы отсутствуют"
        prompt = f"""
Проверь полноту комплекта ИТД для сдачи объекта в эксплуатацию.

Тип объекта: {project_data.get('project_type')}
Наименование: {project_data.get('name')}

Имеющиеся документы:
{doc_list}

На основании СП РК 1.04.02-2019 и нормативов для данного типа объекта:
1. Укажи, какие документы уже есть (отметь ✅)
2. Укажи, каких документов не хватает (отметь ❌)
3. Укажи приоритет оформления недостающих документов
4. Дай рекомендации по устранению замечаний
"""
        return await self.think(prompt, project_type=project_data.get("project_type"))
