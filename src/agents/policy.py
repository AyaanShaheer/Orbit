import uuid
from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.models.graph_nodes import AgentRole, Observation
from src.models.events import AgentTimelineStep

class PolicyAgent(BaseAgent):
    """
    Procedural Memory Specialist.
    Retrieves standard operating procedures, precondition checks, and past blast radiuses from FalkorDB.
    """
    def __init__(self):
        super().__init__("agent-policy", AgentRole.POLICY, "Policy Agent")

    def investigate(self, incident_id: str, episode_id: str, service: str, context: Dict[str, Any]) -> AgentTimelineStep:
        task_id = f"task-policy-rules-{incident_id}"
        self.task_mgr.create_task(task_id, incident_id, "Procedural Policy Guardrail Check", "Validate recovery procedures and precondition constraints")
        self.task_mgr.claim_task(task_id, self.agent_id, expected_version=1)

        # Retrieve procedures
        procs, cypher_ms = self.engine.query_procedures()
        context["procedures"] = procs

        claim_text = (
            "Procedural policy guardrail: Procedure 'PROC-REDIS-RESTART' carries CRITICAL risk level with known failure mode "
            "'Cascading database stampede'. Policy requires non-destructive diagnostics (PROC-INSPECT-POOL) "
            "and saturation verification (<70%) before approving any restart."
        )

        obs_id = f"OBS-POL-{uuid.uuid4().hex[:6].upper()}"
        obs = Observation(
            id=obs_id,
            claim=claim_text,
            source_id=self.agent_id,
            confidence=1.0
        )
        self.engine.add_observation(obs, episode_id, self.agent_id)
        self.task_mgr.complete_task(task_id, self.agent_id)

        context.setdefault("observations", []).append(obs)

        return AgentTimelineStep(
            step_number=3,
            agent_id=self.agent_id,
            agent_role=self.role,
            action="Procedural Guardrail & Risk Verification",
            retrieved_entities=[p.get("procedure_id", "p") for p in procs],
            cypher_queries_executed=["MATCH (p:Procedure) RETURN p.id, p.name, p.preconditions, p.risk_level"],
            observations_produced=[obs_id],
            claims=[claim_text],
            conflicts_detected=[]
        )
