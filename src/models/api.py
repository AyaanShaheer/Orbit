from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.models.graph_nodes import Incident, Decision, Outcome, Task
from src.models.events import AgentTimelineStep, ContradictionItem, MemoryReplaySnapshot

class IncidentInvestigationRequest(BaseModel):
    incident_id: str
    service: str
    severity: str = "critical"
    description: str = ""
    scenario_type: Optional[str] = "redis_saturation_config_mismatch" # scenario identifier

class InvestigationResponse(BaseModel):
    incident_id: str
    status: str
    final_recommendation: str
    decision: Decision
    timeline: List[AgentTimelineStep]
    contradictions: List[ContradictionItem]
    evidence_graph_paths: List[Dict[str, Any]]
    execution_time_ms: float
    graph_query_time_ms: float
    model_inference_time_ms: float

class RecordOutcomeRequest(BaseModel):
    incident_id: str
    decision_id: str
    result: str # "success" or "failure"
    details: str
    impact_level: str = "none"

class InjectFactRequest(BaseModel):
    service: str
    content: str
    memory_type: str # "episodic", "semantic", "procedural"
    confidence: float = 1.0

class TaskClaimRequest(BaseModel):
    task_id: str
    agent_id: str
    expected_version: int

class SystemStatsResponse(BaseModel):
    node_counts: Dict[str, int]
    edge_counts: Dict[str, int]
    active_incidents: int
    active_memory_facts: int
    superseded_facts: int
