from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class DocumentType(str, enum.Enum):
    # Журналы
    OJR = "ojr"                          # Общий журнал работ (СП РК 1.04.02)
    WELDING_JOURNAL = "welding_journal"  # Журнал сварочных работ
    ISOLATION_JOURNAL = "isolation_journal"  # Журнал изоляционных работ
    GEODESY_JOURNAL = "geodesy_journal"  # Геодезический журнал

    # Акты освидетельствования
    AOSR = "aosr"                        # Акт освидетельствования скрытых работ
    INTERMEDIATE_ACCEPTANCE = "intermediate_acceptance"  # Акт промежуточной приемки

    # Испытания
    HYDRAULIC_TEST = "hydraulic_test"   # Акт гидравлических испытаний
    PNEUMATIC_TEST = "pneumatic_test"   # Акт пневматических испытаний
    PURGE_ACT = "purge_act"             # Акт продувки
    TIGHTNESS_TEST = "tightness_test"   # Акт испытания на герметичность

    # Исполнительная документация
    EXECUTIVE_SCHEME = "executive_scheme"  # Исполнительная схема
    BUILDING_PASSPORT = "building_passport"  # Строительный паспорт

    # Акты приемки
    KS2 = "ks2"    # Акт приемки выполненных работ
    KS3 = "ks3"    # Справка о стоимости выполненных работ
    KS11 = "ks11"  # Акт приемки построенного объекта
    KS14 = "ks14"  # Акт приемочной комиссии

    # ПД/РД
    POS = "pos"    # Проект организации строительства
    POR = "por"    # Проект организации работ
    PPR = "ppr"    # Проект производства работ
    TECH_CARD = "tech_card"  # Технологическая карта

    # Сертификаты и паспорта
    MATERIAL_CERT = "material_cert"   # Сертификат на материалы
    EQUIPMENT_PASSPORT = "equipment_passport"  # Паспорт оборудования
    WELDER_CERT = "welder_cert"       # Удостоверение сварщика

    # Разрешения
    CONSTRUCTION_PERMIT = "construction_permit"  # Разрешение на строительство
    COMMISSIONING_ACT = "commissioning_act"       # Акт ввода в эксплуатацию

    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"           # Черновик
    REVIEW = "review"         # На проверке
    APPROVED = "approved"     # Утвержден
    SIGNED = "signed"         # Подписан
    REJECTED = "rejected"     # Отклонен
    ARCHIVED = "archived"     # В архиве


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)

    document_type = Column(Enum(DocumentType), nullable=False)
    document_number = Column(String(100))        # Номер документа
    title = Column(String(500), nullable=False)  # Наименование
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)

    # Content
    content_json = Column(JSON, default=dict)    # Структурированное содержимое
    file_path = Column(String(500))              # Путь к сгенерированному файлу (docx/pdf)
    file_format = Column(String(10))             # docx, pdf

    # Work section reference
    work_section_id = Column(String(36), ForeignKey("work_sections.id"), nullable=True)

    # Signatures
    author = Column(String(200))          # Составил
    checked_by = Column(String(200))      # Проверил
    approved_by = Column(String(200))     # Утвердил
    signed_date = Column(DateTime)

    # Normative references
    normative_refs = Column(JSON, default=list)  # Ссылки на НТД

    # Auto-generation
    auto_generated = Column(Boolean, default=False)
    generation_prompt = Column(Text)

    # Dates
    document_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="documents")
    work_section = relationship("WorkSection", back_populates="documents")
