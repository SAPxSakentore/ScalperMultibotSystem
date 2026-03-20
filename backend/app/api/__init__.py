from app.api.projects import router as projects_router
from app.api.documents import router as documents_router
from app.api.agents import router as agents_router

__all__ = ["projects_router", "documents_router", "agents_router"]
