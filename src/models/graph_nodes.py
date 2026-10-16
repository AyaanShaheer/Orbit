from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class MemoryType(str, Enum):
    EPISODIC = "episodic"       # What happened in a specific session / incident
    SEMANTIC = "semantic"       # What the system currently believes about a service, dependency, config
    PROCEDURAL = "procedural"   # How to perform a task, preconditions, known failure modes

class FactStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONTRADICTED = "contradicted"
    STALE = "stale"
    INVALID = "invalid"

class TaskStatus(str, Enum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class OutcomeResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"

class AgentRole(str, Enum):
    INVESTIGATOR = "investigator"
    SYSTEMS = "systems"
    POLICY = "policy"
    COORDINATOR = "coordinator"

class Agent(BaseModel):
    id: str
    role: AgentRole
    name: str
    status: str = "idle"
    description: Optional[str] = None

class Incident(BaseModel):
    id: str
    service: str
    severity: str = "critical"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active" # active, investigating, resolved, mitigated
    description: str = ""

class Episode(BaseModel):
    id: str
    session_id: str
    incident_id: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None
    status: str = "open"

class Observation(BaseModel):
    id: str
    claim: str
    source_id: str
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = 0.9
    raw_data: Optional[Dict[str, Any]] = None

class MemoryFact(BaseModel):
    id: str
    content: str
    memory_type: MemoryType
    valid_from: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_to: Optional[str] = None
    status: FactStatus = FactStatus.ACTIVE
    service: Optional[str] = None
    superseded_by: Optional[str] = None
    confidence: float = 1.0

class Decision(BaseModel):
    id: str
    incident_id: str
    action: str
    rationale: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recommended_by: str = "coordinator"
    status: str = "pending" # pending, executed, skipped

class Task(BaseModel):
    id: str
    incident_id: str
    name: str
    owner_id: Optional[str] = None
    status: TaskStatus = TaskStatus.UNCLAIMED
    version: int = 1
    description: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Outcome(BaseModel):
    id: str
    decision_id: str
    result: OutcomeResult
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: str = ""
    impact_level: str = "none" # increased, mitigated, neutral

class Procedure(BaseModel):
    id: str
    name: str
    preconditions: str
    risk_level: str = "medium" # low, medium, high, critical
    failure_modes: Optional[str] = None

class Service(BaseModel):
    id: str
    name: str
    version: str
    cache_type: str = "redis_standalone"
    pool_size: int = 10
    timeout_ms: int = 2000
    config_summary: str = ""
