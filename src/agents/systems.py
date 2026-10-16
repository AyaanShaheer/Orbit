import uuid
from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.models.graph_nodes import AgentRole, Observation
from src.models.events import AgentTimelineStep

class SystemsAgent(BaseAgent):
    """
    Semantic Memory Specialist.
    Traverses the live dependency graph and verifies whether historical facts still apply
    to current service version and infrastructure configuration.
    """
    def __init__(self):
        super().__init__("agent-systems", AgentRole.SYSTEMS, "Systems Agent")

    def investigate(self, incident_id: str, episode_id: str, service: str, context: Dict[str, Any]) -> AgentTimelineStep:
        task_id = f"task-sys-topology-{incident_id}"
        self.task_mgr.create_task(task_id, incident_id, "Semantic Topology Verification", "Check service configuration and dependency drift")
        self.task_mgr.claim_task(task_id, self.agent_id, expected_version=1)

        # Query semantic memory for service topology
        svc_info, cypher_ms = self.engine.query_service_topology_and_facts(service)
        context["service_topology"] = svc_info

        version = svc_info.get("version", "unknown")
        cache_type = svc_info.get("cache_type", "unknown")
        pool_size = svc_info.get("pool_size", 0)
        deps = svc_info.get("dependencies", [])

        claim_text = (
            f"Active semantic verification: {service} is running v{version} configured with {cache_type} "
            f"(connection pool={pool_size}, dependencies={deps}). This configuration differs materially from legacy standalone Redis."
        )

        obs_id = f"OBS-SYS-{uuid.uuid4().hex[:6].upper()}"
        obs = Observation(
            id=obs_id,
            claim=claim_text,
            source_id=self.agent_id,
            confidence=0.98,
            raw_data={"version": version, "cache_type": cache_type, "pool_size": pool_size}
        )
        self.engine.add_observation(obs, episode_id, self.agent_id)
        self.task_mgr.complete_task(task_id, self.agent_id)

        context.setdefault("observations", []).append(obs)

        return AgentTimelineStep(
            step_number=2,
            agent_id=self.agent_id,
            agent_role=self.role,
            action="Semantic Topology & Configuration Traversal",
            retrieved_entities=[svc_info.get("service_id", "svc-checkout")] + [f"dep:{d}" for d in deps],
            cypher_queries_executed=[
                f"MATCH (s:Service {{name: '{service}'}}) OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep) OPTIONAL MATCH (s)-[:HAS_FACT]->(f) RETURN s, dep, f"
            ],
            observations_produced=[obs_id],
            claims=[claim_text],
            conflicts_detected=[]
        )
