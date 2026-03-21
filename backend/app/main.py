from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import init_db
from app.api.projects import router as projects_router
from app.api.documents import router as documents_router
from app.api.agents import router as agents_router
from app.api.shift_reports import router as shift_reports_router
from app.api.work_sections import router as work_sections_router
from app.api.smeta import router as smeta_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация базы данных
    await init_db()

    # Создание директорий для хранения файлов
    os.makedirs(settings.DOCS_STORAGE_PATH, exist_ok=True)

    print(f"🏗️  {settings.APP_NAME} v{settings.APP_VERSION} запущен")
    print(f"📋 Режим: {'ОФФЛАЙН' if settings.OFFLINE_MODE else 'ОНЛАЙН'}")
    print(f"🤖 Claude модель: {settings.CLAUDE_MODEL}")

    yield

    print("👋 Завершение работы KazBuildOS")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — разрешаем frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production заменить на конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API роутеры
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(agents_router)
app.include_router(shift_reports_router)
app.include_router(work_sections_router)
app.include_router(smeta_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "offline_mode": settings.OFFLINE_MODE,
    }


@app.get("/api/stats")
async def get_stats():
    """Расширенная статистика системы для дашборда и страницы Statistics."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.project import Project, ProjectStatus, ProjectType
    from app.models.document import Document, DocumentType, DocumentStatus
    from app.models.shift_report import ShiftReport

    async with AsyncSessionLocal() as db:
        # --- Проекты ---
        projects_count = (await db.execute(select(func.count()).select_from(Project))).scalar()
        active_projects = (await db.execute(
            select(func.count()).select_from(Project)
            .where(Project.status.in_([
                ProjectStatus.CONSTRUCTION, ProjectStatus.TESTING, ProjectStatus.COMMISSIONING,
            ]))
        )).scalar()

        # Проекты по статусу
        status_rows = (await db.execute(
            select(Project.status, func.count()).group_by(Project.status)
        )).all()
        projects_by_status = {r[0]: r[1] for r in status_rows}

        # Проекты по типу
        type_rows = (await db.execute(
            select(Project.project_type, func.count()).group_by(Project.project_type)
        )).all()
        projects_by_type = {r[0]: r[1] for r in type_rows}

        # --- Документы ---
        docs_count = (await db.execute(select(func.count()).select_from(Document))).scalar()
        signed_docs = (await db.execute(
            select(func.count()).select_from(Document)
            .where(Document.status.in_([DocumentStatus.APPROVED, DocumentStatus.SIGNED]))
        )).scalar()
        draft_docs = (await db.execute(
            select(func.count()).select_from(Document).where(Document.status == DocumentStatus.DRAFT)
        )).scalar()

        # Документы по типу
        doc_type_rows = (await db.execute(
            select(Document.document_type, func.count()).group_by(Document.document_type)
        )).all()
        docs_by_type = {r[0]: r[1] for r in doc_type_rows}

        # --- Сменные рапорты ---
        reports_count = (await db.execute(select(func.count()).select_from(ShiftReport))).scalar()
        finalized_count = (await db.execute(
            select(func.count()).select_from(ShiftReport).where(ShiftReport.is_finalized == True)
        )).scalar()

        # Рапорты по месяцам (последние 6 мес.)
        monthly_rows = (await db.execute(
            select(
                func.strftime('%Y-%m', ShiftReport.shift_date).label('month'),
                func.count()
            )
            .group_by(func.strftime('%Y-%m', ShiftReport.shift_date))
            .order_by(func.strftime('%Y-%m', ShiftReport.shift_date).desc())
            .limit(6)
        )).all()
        reports_by_month = [{"month": r[0], "count": r[1]} for r in reversed(monthly_rows)]

    return {
        "projects": {
            "total": projects_count,
            "active": active_projects,
            "by_status": projects_by_status,
            "by_type": projects_by_type,
        },
        "documents": {
            "total": docs_count,
            "signed": signed_docs,
            "draft": draft_docs,
            "by_type": docs_by_type,
        },
        "shift_reports": {
            "total": reports_count,
            "finalized": finalized_count,
            "by_month": reports_by_month,
        },
    }


@app.get("/api/normatives")
async def get_normatives():
    """Получить список нормативных документов РК."""
    from app.services.normative_base import NORMATIVE_DB
    return [
        {
            "code": doc.code,
            "title": doc.title,
            "category": doc.category,
            "applies_to": doc.applies_to,
        }
        for doc in NORMATIVE_DB.values()
    ]
