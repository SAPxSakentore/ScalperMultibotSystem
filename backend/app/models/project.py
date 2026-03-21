from sqlalchemy import Column, String, Text, DateTime, Float, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import TEXT
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ProjectType(str, enum.Enum):
    GAS_PIPELINE_HIGH = "gas_pipeline_high"      # Магистральный газопровод высокого давления
    GAS_PIPELINE_MEDIUM = "gas_pipeline_medium"   # Газопровод среднего давления
    GAS_PIPELINE_LOW = "gas_pipeline_low"         # Газопровод низкого давления
    OIL_PIPELINE = "oil_pipeline"                  # Нефтепровод
    WATER_PIPELINE = "water_pipeline"              # Водопровод
    INDUSTRIAL_BUILDING = "industrial_building"    # Промышленное здание
    ROAD = "road"                                  # Дорога
    OTHER = "other"


class ProjectStatus(str, enum.Enum):
    INITIATION = "initiation"           # Инициация
    DESIGN = "design"                   # Проектирование
    PERMITS = "permits"                 # Согласования/экспертиза
    PROCUREMENT = "procurement"         # Закупки
    CONSTRUCTION = "construction"       # Строительство
    TESTING = "testing"                 # Испытания
    COMMISSIONING = "commissioning"     # Пуско-наладка
    ACCEPTANCE = "acceptance"           # Приемка
    COMPLETED = "completed"             # Завершен
    SUSPENDED = "suspended"             # Приостановлен


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False)  # Шифр проекта
    name = Column(String(500), nullable=False)
    description = Column(Text)
    project_type = Column(Enum(ProjectType), nullable=False)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.INITIATION)

    # Location
    region = Column(String(200))        # Область
    district = Column(String(200))      # Район
    locality = Column(String(200))      # Населенный пункт
    coordinates = Column(String(100))   # GPS координаты трассы

    # Pipeline specific (for gas/oil pipelines)
    total_length_km = Column(Float)     # Общая длина, км
    diameter_mm = Column(Float)         # Диаметр трубы, мм
    working_pressure_mpa = Column(Float)  # Рабочее давление, МПа
    design_pressure_mpa = Column(Float)   # Расчетное давление, МПа

    # Parties
    customer_name = Column(String(500))       # Заказчик
    customer_bin = Column(String(12))         # БИН заказчика
    contractor_name = Column(String(500))     # Генподрядчик
    contractor_bin = Column(String(12))       # БИН подрядчика
    designer_name = Column(String(500))       # Проектировщик
    designer_bin = Column(String(12))         # БИН проектировщика
    technical_supervisor = Column(String(200))  # Технический надзор заказчика

    # Documents
    design_doc_number = Column(String(100))   # Номер проектной документации
    permit_number = Column(String(100))        # Разрешение на строительство

    # Dates
    start_date = Column(DateTime)
    planned_end_date = Column(DateTime)
    actual_end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    metadata_json = Column(JSON, default=dict)

    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    work_sections = relationship("WorkSection", back_populates="project", cascade="all, delete-orphan")
    shift_reports = relationship("ShiftReport", back_populates="project", cascade="all, delete-orphan")
    pdf_uploads = relationship("ProjectPdfUpload", back_populates="project", cascade="all, delete-orphan")
    smeta_items = relationship("SmetaItem", back_populates="project", cascade="all, delete-orphan", order_by="SmetaItem.position_no")
