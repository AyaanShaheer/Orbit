import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from src.agents.base import BaseAgent
from src.models.graph_nodes import AgentRole, Observation
from src.models.events import AgentTimelineStep

class InvestigatorAgent(BaseAgent):
    """
    Episodic Memory Specialist.
    Retrieves historical incidents, past hypotheses, prior attempted actions, and outcomes from FalkorDB.
    """
    def __init__(self):
        super().__init__("agent-investigator", AgentRole.INVESTIGATOR, "Investigator Agent")

    def investigate(self, incident_id: str, episode_id: str, service: str, context: Dict[str, Any]) -> AgentTimelineStep:
        task_id = f"task-inv-history-{incident_id}"
        # Claim coordination task
        self.task_mgr.create_task(task_id, incident_id, "Historical Episodic Recall", "Retrieve past incident outcomes and hypotheses")
        claim_res = self.task_mgr.claim_task(task_id, self.agent_id, expected_version=1)

        # Execute Multi-hop Cypher Query
        history_rows, cypher_ms = self.engine.query_prior_incident_outcomes(service)
        context["historical_outcomes"] = history_rows

        # Formulate observation
        claims = []
        retrieved_entities = []
        if history_rows:
            top_hist = history_rows[0]
            claim_text = (
                f"Historical incident {top_hist.get('incident_id')} associated checkout timeouts with "
                f"cache connection saturation. Past action '{top_hist.get('action')}' had outcome '{top_hist.get('outcome')}'."
            )
            claims.append(claim_text)
            retrieved_entities.extend([top_hist.get('incident_id'), top_hist.get('decision_id'), top_hist.get('outcome_id')])
        else:
            claims.append(f"No prior incidents recorded for service {service}.")

        # Ingest observation into FalkorDB
        obs_id = f"OBS-INV-{uuid.uuid4().hex[:6].upper()}"
        obs = Observation(
            id=obs_id,
            claim=claims[0],
            source_id=self.agent_id,
            confidence=0.95
        )
        self.engine.add_observation(obs, episode_id, self.agent_id)
        self.task_mgr.complete_task(task_id, self.agent_id)

        context.setdefault("observations", []).append(obs)

        return AgentTimelineStep(
            step_number=1,
            agent_id=self.agent_id,
            agent_role=self.role,
            action="Episodic Memory Graph Retrieval",
            retrieved_entities=retrieved_entities,
            cypher_queries_executed=[
                f"MATCH (i:Incident {{service: '{service}'}})-[:HAS_EPISODE]->(e)-[:CONTAINS]->(o)-[:SUPPORTS]->(f) MATCH (f)-[:RELATED_TO]->(d)-[:RESULTED_IN]->(out) RETURN i, o, f, d, out"
            ],
            observations_produced=[obs_id],
            claims=claims,
            conflicts_detected=[]
        )
