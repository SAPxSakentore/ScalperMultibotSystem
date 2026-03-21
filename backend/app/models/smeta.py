"""
Модель сметных позиций проекта (Смета / Сметные расчёты).
Каждая позиция — строка сметы с единичной расценкой.
Используется для расчёта КС-2 и КС-3 по факту из сменных рапортов.
"""
from sqlalchemy import Column, String, Text, Float, Integer, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class SmetaItem(Base):
    """
    Позиция сметы по проекту.
    work_type_key — ключ для сопоставления с works_done[].work_type из рапортов.
    """
    __tablename__ = "smeta_items"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Позиция в смете
    position_no    = Column(Integer, nullable=False, default=1)   # 1, 2, 3...
    section        = Column(String(200), default="")               # Раздел/глава сметы
    name           = Column(String(500), nullable=False)           # Наименование работ
    work_type_key  = Column(String(200), default="")               # Ключ для матчинга с рапортами

    unit           = Column(String(50), nullable=False)            # Ед. изм.
    unit_price     = Column(Float, nullable=False, default=0.0)    # Расценка за ед., тг.
    planned_qty    = Column(Float, nullable=False, default=0.0)    # Объём по смете

    # Вспомогательные данные
    normative_code = Column(String(100), default="")               # ТЕР/ФЕР/ЛоКС код
    notes          = Column(Text, default="")
    is_active      = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="smeta_items")

    @property
    def planned_amount(self) -> float:
        return round(self.unit_price * self.planned_qty, 2)
