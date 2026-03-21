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
    """Статистика системы для дашборда."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.project import Project
    from app.models.document import Document
    from app.models.shift_report import ShiftReport

    async with AsyncSessionLocal() as session:
        projects_count = (await session.execute(select(func.count()).select_from(Project))).scalar()
        docs_count = (await session.execute(select(func.count()).select_from(Document))).scalar()
        reports_count = (await session.execute(select(func.count()).select_from(ShiftReport))).scalar()
        finalized_count = (await session.execute(
            select(func.count()).select_from(ShiftReport).where(ShiftReport.is_finalized == True)
        )).scalar()

    return {
        "projects": projects_count,
        "documents": docs_count,
        "shift_reports": reports_count,
        "finalized_reports": finalized_count,
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
