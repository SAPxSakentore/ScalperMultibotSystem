from app.agents.ceo import CEOAgent
from app.agents.project_manager import ProjectManagerAgent
from app.agents.chief_engineer import ChiefEngineerAgent
from app.agents.documentation_manager import DocumentationManagerAgent
from app.agents.quality_control import QualityControlAgent
from app.agents.hse_officer import HSEOfficerAgent
from app.agents.estimator import EstimatorAgent
from app.agents.legal_compliance import LegalComplianceAgent
from app.agents.field_inspector import FieldInspectorAgent

# Реестр всех агентов
AGENTS_REGISTRY = {
    "ceo": CEOAgent,
    "project_manager": ProjectManagerAgent,
    "chief_engineer": ChiefEngineerAgent,
    "documentation_manager": DocumentationManagerAgent,
    "quality_control": QualityControlAgent,
    "hse_officer": HSEOfficerAgent,
    "estimator": EstimatorAgent,
    "legal_compliance": LegalComplianceAgent,
    "field_inspector": FieldInspectorAgent,
}

# Инстансы агентов (синглтоны)
_agent_instances = {}


def get_agent(role: str):
    """Получить экземпляр агента по роли."""
    if role not in _agent_instances:
        if role not in AGENTS_REGISTRY:
            raise ValueError(f"Агент с ролью '{role}' не найден")
        _agent_instances[role] = AGENTS_REGISTRY[role]()
    return _agent_instances[role]


def get_all_agents():
    """Получить все агенты."""
    return [get_agent(role) for role in AGENTS_REGISTRY]


__all__ = [
    "CEOAgent", "ProjectManagerAgent", "ChiefEngineerAgent",
    "DocumentationManagerAgent", "QualityControlAgent", "HSEOfficerAgent",
    "EstimatorAgent", "LegalComplianceAgent", "FieldInspectorAgent",
    "AGENTS_REGISTRY", "get_agent", "get_all_agents",
]
