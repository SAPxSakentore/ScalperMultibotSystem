from sqlalchemy import Column, String, Text, DateTime, Float, Enum, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class WorkSectionStatus(str, enum.Enum):
    PLANNED = "planned"           # Запланировано
    IN_PROGRESS = "in_progress"   # Выполняется
    COMPLETED = "completed"       # Выполнено
    ACCEPTED = "accepted"         # Принято
    REJECTED = "rejected"         # Отклонено


class WorkSection(Base):
    """Раздел/этап работ проекта (участок трубопровода, конструктив и т.д.)"""
    __tablename__ = "work_sections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    parent_id = Column(String(36), ForeignKey("work_sections.id"), nullable=True)

    code = Column(String(50))           # Шифр раздела
    name = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(Enum(WorkSectionStatus), default=WorkSectionStatus.PLANNED)

    # For pipelines: chainage (пикеты)
    chainage_start = Column(Float)   # ПК начало
    chainage_end = Column(Float)     # ПК конец
    length_m = Column(Float)         # Длина, м

    # Responsible persons
    responsible_foreman = Column(String(200))  # Прораб
    responsible_engineer = Column(String(200)) # ИТР

    # Dates
    planned_start = Column(DateTime)
    planned_end = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)

    # Progress
    progress_percent = Column(Float, default=0.0)

    # Metadata
    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="work_sections")
    documents = relationship("Document", back_populates="work_section")
    children = relationship("WorkSection", backref="parent", remote_side=[id])
