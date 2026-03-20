from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AgentRole(str, enum.Enum):
    CEO = "ceo"                           # Генеральный директор
    PROJECT_MANAGER = "project_manager"   # Руководитель проекта / ГИП
    CHIEF_ENGINEER = "chief_engineer"     # Главный инженер
    DOCUMENTATION_MANAGER = "documentation_manager"  # Ведущий специалист ИТД
    QUALITY_CONTROL = "quality_control"   # Технический надзор / ОТК
    HSE_OFFICER = "hse_officer"           # Специалист ОТ и ПБ
    ESTIMATOR = "estimator"               # Ведущий сметчик
    LEGAL_COMPLIANCE = "legal_compliance" # Юрисконсульт / нормативщик
    FIELD_INSPECTOR = "field_inspector"   # Производитель работ (прораб)


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    OFFLINE = "offline"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role = Column(Enum(AgentRole), unique=True, nullable=False)

    # Identity
    name_ru = Column(String(200), nullable=False)   # ФИО на русском
    name_kz = Column(String(200))                    # ФИО на казахском
    position = Column(String(300), nullable=False)   # Должность
    avatar_initials = Column(String(3))              # Инициалы для аватара

    # Status
    status = Column(Enum(AgentStatus), default=AgentStatus.IDLE)
    current_task = Column(Text)

    # Capabilities
    capabilities = Column(JSON, default=list)        # Список возможностей
    system_prompt = Column(Text, nullable=False)     # System prompt для Claude

    # Stats
    tasks_completed = Column(Integer, default=0)
    documents_generated = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=True)

    agent_role = Column(Enum(AgentRole), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Input/Output
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    result_text = Column(Text)

    # Status
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    error_message = Column(Text)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # FK
    project = None  # Defined in Project model via backref


# Override Task.project relationship
from sqlalchemy.orm import relationship
Task.project = relationship("Project", foreign_keys=[Task.project_id],
                             primaryjoin="Task.project_id == Project.id",
                             backref="tasks", lazy="select")
