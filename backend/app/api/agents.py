from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.agents import get_agent, get_all_agents, AGENTS_REGISTRY

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentChatRequest(BaseModel):
    message: str
    project_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    agent_role: str
    agent_name: str
    agent_position: str
    message: str
    response: str


@router.get("/")
async def list_agents():
    """Получить список всех агентов-сотрудников."""
    return [agent.to_dict() for agent in get_all_agents()]


@router.get("/{role}")
async def get_agent_info(role: str):
    """Получить информацию об агенте."""
    if role not in AGENTS_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Агент '{role}' не найден")
    agent = get_agent(role)
    return agent.to_dict()


@router.post("/{role}/chat", response_model=AgentChatResponse)
async def chat_with_agent(role: str, request: AgentChatRequest):
    """Отправить сообщение агенту и получить ответ."""
    if role not in AGENTS_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Агент '{role}' не найден")

    agent = get_agent(role)
    response = await agent.think(
        request.message,
        context=request.context,
        project_type=request.project_type,
    )

    return AgentChatResponse(
        agent_role=agent.role,
        agent_name=agent.name_ru,
        agent_position=agent.position,
        message=request.message,
        response=response,
    )


@router.get("/roles/all")
async def get_all_roles():
    """Получить все доступные роли агентов."""
    return list(AGENTS_REGISTRY.keys())
