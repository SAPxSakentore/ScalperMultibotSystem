from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AgentRole(str, enum.Enum):
    CEO = "ceo"
    PROJECT_MANAGER = "project_manager"
    CHIEF_ENGINEER = "chief_engineer"
    DOCUMENTATION_MANAGER = "documentation_manager"
    QUALITY_CONTROL = "quality_control"
    HSE_OFFICER = "hse_officer"
    ESTIMATOR = "estimator"
    LEGAL_COMPLIANCE = "legal_compliance"
    FIELD_INSPECTOR = "field_inspector"


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    OFFLINE = "offline"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role = Column(Enum(AgentRole), unique=True, nullable=False)

    name_ru = Column(String(200), nullable=False)
    name_kz = Column(String(200))
    position = Column(String(300), nullable=False)
    avatar_initials = Column(String(3))

    status = Column(Enum(AgentStatus), default=AgentStatus.IDLE)
    current_task = Column(Text)

    capabilities = Column(JSON, default=list)
    system_prompt = Column(Text, nullable=False)

    tasks_completed = Column(Integer, default=0)
    documents_generated = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    agent_role = Column(Enum(AgentRole), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    result_text = Column(Text)

    status = Column(String(50), default="pending")
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    project = relationship("Project", foreign_keys=[project_id], back_populates="tasks")
