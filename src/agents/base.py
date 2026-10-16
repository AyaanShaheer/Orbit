import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.models.graph_nodes import AgentRole
from src.models.events import AgentTimelineStep
from src.memory.engine import memory_engine
from src.coordination.task_manager import task_manager

class BaseAgent(ABC):
    def __init__(self, agent_id: str, role: AgentRole, name: str):
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.engine = memory_engine
        self.task_mgr = task_manager

    @abstractmethod
    def investigate(self, incident_id: str, episode_id: str, service: str, context: Dict[str, Any]) -> AgentTimelineStep:
        """Execute agent investigation step and return an auditable timeline record."""
        pass
