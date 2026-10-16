from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from src.models.graph_nodes import AgentRole, FactStatus

class ContradictionItem(BaseModel):
    prior_fact_id: str
    prior_fact_content: str
    prior_service_version: Optional[str] = None
    new_claim: str
    new_source_agent: str
    reason: str
    resolution: str # e.g., "superseded", "differentiated_by_version", "precondition_enforced"
    supporting_graph_path: List[str] = Field(default_factory=list)

class AgentTimelineStep(BaseModel):
    step_number: int
    agent_id: str
    agent_role: AgentRole
    action: str
    retrieved_entities: List[str] = Field(default_factory=list)
    cypher_queries_executed: List[str] = Field(default_factory=list)
    observations_produced: List[str] = Field(default_factory=list)
    claims: List[str] = Field(default_factory=list)
    conflicts_detected: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MemoryReplaySnapshot(BaseModel):
    incident_id: str
    decision_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active_facts_at_decision: List[Dict[str, Any]] = Field(default_factory=list)
    agent_disagreements: List[Dict[str, Any]] = Field(default_factory=list)
    critical_evidence_path: List[Dict[str, Any]] = Field(default_factory=list)
    chosen_action: str
    rationale: str
    lesson_learned_afterward: Optional[str] = None

class TaskClaimResult(BaseModel):
    task_id: str
    agent_id: str
    claimed: bool
    version_observed: int
    new_version: int
    error_message: Optional[str] = None
