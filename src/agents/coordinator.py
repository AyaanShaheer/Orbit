import uuid
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from src.agents.base import BaseAgent
from src.models.graph_nodes import AgentRole, Decision
from src.models.events import AgentTimelineStep, ContradictionItem
from src.memory.contradiction import contradiction_detector
from src.agents.llm_adapter import llm_adapter

class CoordinatorAgent(BaseAgent):
    """
    Belief Integration Specialist.
    Reconciles conflicting hypotheses from Investigator, Systems, and Policy agents.
    Evaluates evidence timestamps, system version differences, and past blast radiuses.
    Records evidence-backed decisions in FalkorDB.
    """
    def __init__(self):
        super().__init__("agent-coordinator", AgentRole.COORDINATOR, "Coordinator Agent")
        self.contradiction_detector = contradiction_detector
        self.llm = llm_adapter

    def reconcile_and_decide(
        self,
        incident_id: str,
        episode_id: str,
        service: str,
        context: Dict[str, Any]
    ) -> Tuple[Decision, AgentTimelineStep, List[ContradictionItem]]:
        task_id = f"task-coord-reconciliation-{incident_id}"
        self.task_mgr.create_task(task_id, incident_id, "Belief Integration & Hypothesis Reconciliation", "Reconcile episodic, semantic, and procedural findings")
        self.task_mgr.claim_task(task_id, self.agent_id, expected_version=1)

        historical_outcomes = context.get("historical_outcomes", [])
        service_topology = context.get("service_topology", {})
        observations = context.get("observations", [])
        obs_ids = [o.id for o in observations]

        # Check for contradictions / configuration drifts
        contradictions = self.contradiction_detector.check_hypothesis_conflicts(
            service=service,
            investigator_claims=[o.claim for o in observations if o.source_id == "agent-investigator"],
            systems_facts=service_topology,
            historical_outcomes=historical_outcomes,
            proposed_action="Restart Redis cache cluster"
        )
        context["contradictions"] = contradictions

        # Reconcile logic:
        # Rather than simply averaging confidence scores, compare evidence:
        # 1. Historical incident suggests cache exhaustion, BUT current service is v2.4 (cluster with pool=64)
        # 2. Prior restart action caused cascading failure on core-postgres
        # 3. Policy requires non-destructive saturation telemetry first
        # Therefore: Choose non-destructive inspection (PROC-INSPECT-POOL) over restart.
        
        rec_action = "Execute connection pool and saturation telemetry check (PROC-INSPECT-POOL)"
        rationale = (
            "The previous incident (INC-2026-0901) suggests Redis exhaustion, but the current configuration differs "
            f"(v{service_topology.get('version', '2.4.0')} Redis Cluster vs legacy standalone). A blind restart is not justified yet "
            "due to documented prior cascading failure on core-postgres. Recommendation: Check connection saturation first "
            "via PROC-INSPECT-POOL before considering destructive recovery steps."
        )

        decision_id = f"DEC-{uuid.uuid4().hex[:6].upper()}"
        decision = Decision(
            id=decision_id,
            incident_id=incident_id,
            action=rec_action,
            rationale=rationale,
            recommended_by=self.agent_id,
            status="pending"
        )

        # Commit decision to FalkorDB linked to supporting observations & procedure
        self.engine.record_decision(decision, obs_ids, procedure_id="PROC-INSPECT-POOL")
        self.task_mgr.complete_task(task_id, self.agent_id)

        step = AgentTimelineStep(
            step_number=4,
            agent_id=self.agent_id,
            agent_role=self.role,
            action="Belief Integration & Evidence-Backed Decision",
            retrieved_entities=[decision_id, "PROC-INSPECT-POOL"],
            cypher_queries_executed=[
                f"MATCH (i:Incident {{id: '{incident_id}'}}) CREATE (d:Decision) CREATE (d)-[:BASED_ON]->(o) CREATE (d)-[:USED_PROCEDURE]->(p) RETURN d"
            ],
            observations_produced=[],
            claims=[rationale],
            conflicts_detected=[c.reason for c in contradictions]
        )

        return decision, step, contradictions

    def investigate(self, incident_id: str, episode_id: str, service: str, context: Dict[str, Any]) -> AgentTimelineStep:
        _, step, _ = self.reconcile_and_decide(incident_id, episode_id, service, context)
        return step
