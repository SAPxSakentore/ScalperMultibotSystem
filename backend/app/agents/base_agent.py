"""
Базовый класс для всех AI-агентов (ботов-сотрудников) KazBuildOS.
Использует Anthropic Claude API.
"""
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from abc import ABC, abstractmethod

import anthropic

from app.core.config import settings
from app.services.normative_base import get_normative_summary_for_prompt


class BaseAgent(ABC):
    """Базовый ИИ-агент."""

    role: str = "base"
    name_ru: str = "Базовый агент"
    position: str = "Сотрудник"
    avatar_initials: str = "???"

    def __init__(self):
        self._client: Optional[anthropic.AsyncAnthropic] = None
        if settings.ANTHROPIC_API_KEY:
            self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        pass

    @property
    def capabilities(self) -> List[str]:
        return []

    async def think(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        project_type: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str:
        """
        Отправить запрос агенту и получить ответ.
        В оффлайн режиме (без API ключа) возвращает заглушку.
        """
        if not self._client or settings.OFFLINE_MODE:
            return self._offline_response(user_message, context)

        system = self.system_prompt
        if project_type:
            normative_context = get_normative_summary_for_prompt(project_type)
            system = f"{system}\n\n{normative_context}"

        messages = [{"role": "user", "content": user_message}]
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            messages[0]["content"] = f"Контекст проекта:\n{context_str}\n\n{user_message}"

        try:
            response = await self._client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.APIConnectionError:
            settings.OFFLINE_MODE = True
            return self._offline_response(user_message, context)
        except anthropic.AuthenticationError:
            return "⚠️ Ошибка авторизации API. Проверьте ANTHROPIC_API_KEY."
        except Exception as e:
            return f"⚠️ Ошибка агента {self.name_ru}: {str(e)}"

    def _offline_response(self, message: str, context: Optional[Dict] = None) -> str:
        return (
            f"[{self.name_ru} — ОФФЛАЙН РЕЖИМ]\n"
            f"Запрос принят: {message[:100]}...\n"
            f"Для полноценной работы агента требуется подключение к интернету и API ключ."
        )

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "name_ru": self.name_ru,
            "position": self.position,
            "avatar_initials": self.avatar_initials,
            "capabilities": self.capabilities,
        }
