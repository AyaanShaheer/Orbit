import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from src.db.client import db_client
from src.models.graph_nodes import (
    Incident, Episode, Observation, MemoryFact, Decision, Task, Outcome, Procedure, Service,
    MemoryType, FactStatus, TaskStatus, OutcomeResult
)

logger = logging.getLogger("orbit.memory.engine")

class MemoryEngine:
    """
    Authoritative Graph Memory Engine for ORBIT.
    Manages episodic, semantic, and procedural memories, provenance tracking,
    and temporal supersession in FalkorDB.
    """
    def __init__(self):
        self.client = db_client

    def create_incident(self, incident_id: str, service: str, severity: str = "critical", description: str = "") -> Incident:
        """Create or merge an incident node and associate it with its affected service."""
        cypher = """
        MATCH (s:Service {name: $service})
        MERGE (i:Incident {id: $incident_id})
        ON CREATE SET 
            i.service = $service,
            i.severity = $severity,
            i.created_at = $created_at,
            i.status = 'active',
            i.description = $description
        MERGE (i)-[:AFFECTS]->(s)
        RETURN i
        """
        params = {
            "incident_id": incident_id,
            "service": service,
            "severity": severity,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": description
        }
        self.client.execute_write(cypher, params)
        return Incident(id=incident_id, service=service, severity=severity, description=description)

    def create_episode(self, episode_id: str, incident_id: str, session_id: str) -> Episode:
        """Create an investigation episode connected to an incident."""
        cypher = """
        MATCH (i:Incident {id: $incident_id})
        MERGE (e:Episode {id: $episode_id})
        ON CREATE SET
            e.session_id = $session_id,
            e.incident_id = $incident_id,
            e.started_at = $started_at,
            e.status = 'open'
        MERGE (i)-[:HAS_EPISODE]->(e)
        RETURN e
        """
        params = {
            "episode_id": episode_id,
            "incident_id": incident_id,
            "session_id": session_id,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        self.client.execute_write(cypher, params)
        return Episode(id=episode_id, session_id=session_id, incident_id=incident_id)

    def add_observation(self, observation: Observation, episode_id: str, agent_id: str) -> Observation:
        """Add an observation contributed by an agent and contained within an episode."""
        cypher = """
        MATCH (e:Episode {id: $episode_id})
        MATCH (a:Agent {id: $agent_id})
        MERGE (o:Observation {id: $obs_id})
        ON CREATE SET
            o.claim = $claim,
            o.source_id = $agent_id,
            o.observed_at = $observed_at,
            o.confidence = $confidence
        MERGE (a)-[:CONTRIBUTED]->(o)
        MERGE (e)-[:CONTAINS]->(o)
        RETURN o
        """
        params = {
            "episode_id": episode_id,
            "agent_id": agent_id,
            "obs_id": observation.id,
            "claim": observation.claim,
            "observed_at": observation.observed_at,
            "confidence": observation.confidence
        }
        self.client.execute_write(cypher, params)
        return observation

    def record_decision(self, decision: Decision, observation_ids: List[str], procedure_id: Optional[str] = None) -> Decision:
        """Record an incident decision based on observations and an optional procedure."""
        cypher = """
        MATCH (i:Incident {id: $incident_id})
        MERGE (d:Decision {id: $decision_id})
        ON CREATE SET
            d.incident_id = $incident_id,
            d.action = $action,
            d.rationale = $rationale,
            d.created_at = $created_at,
            d.recommended_by = $recommended_by,
            d.status = $status
        RETURN d
        """
        params = {
            "incident_id": decision.incident_id,
            "decision_id": decision.id,
            "action": decision.action,
            "rationale": decision.rationale,
            "created_at": decision.created_at,
            "recommended_by": decision.recommended_by,
            "status": decision.status
        }
        self.client.execute_write(cypher, params)

        # Link to observations
        for obs_id in observation_ids:
            obs_cypher = """
            MATCH (d:Decision {id: $decision_id})
            MATCH (o:Observation {id: $obs_id})
            MERGE (d)-[:BASED_ON]->(o)
            """
            self.client.execute_write(obs_cypher, {"decision_id": decision.id, "obs_id": obs_id})

        # Link to procedure if applicable
        if procedure_id:
            proc_cypher = """
            MATCH (d:Decision {id: $decision_id})
            MATCH (p:Procedure {id: $procedure_id})
            MERGE (d)-[:USED_PROCEDURE]->(p)
            """
            self.client.execute_write(proc_cypher, {"decision_id": decision.id, "procedure_id": procedure_id})

        return decision

    def record_outcome(self, outcome: Outcome, decision_id: str, new_lesson: Optional[str] = None) -> Tuple[Outcome, Optional[MemoryFact]]:
        """
        Record the verified outcome of a decision.
        If a new lesson is provided, write it as a MemoryFact linked to the decision and outcome.
        """
        cypher = """
        MATCH (d:Decision {id: $decision_id})
        MERGE (out:Outcome {id: $outcome_id})
        ON CREATE SET
            out.decision_id = $decision_id,
            out.result = $result,
            out.verified_at = $verified_at,
            out.details = $details,
            out.impact_level = $impact_level
        MERGE (d)-[:RESULTED_IN]->(out)
        SET d.status = 'executed'
        RETURN out
        """
        params = {
            "decision_id": decision_id,
            "outcome_id": outcome.id,
            "result": outcome.result.value if hasattr(outcome.result, 'value') else outcome.result,
            "verified_at": outcome.verified_at,
            "details": outcome.details,
            "impact_level": outcome.impact_level
        }
        self.client.execute_write(cypher, params)

        new_fact = None
        if new_lesson:
            fact_id = f"FACT-LESSON-{uuid.uuid4().hex[:8].upper()}"
            fact_cypher = """
            MATCH (d:Decision {id: $decision_id})
            MATCH (out:Outcome {id: $outcome_id})
            MATCH (i:Incident {id: d.incident_id})
            MERGE (f:MemoryFact {id: $fact_id})
            ON CREATE SET
                f.content = $content,
                f.memory_type = 'procedural',
                f.valid_from = $valid_from,
                f.status = 'active',
                f.service = i.service,
                f.confidence = 1.0
            MERGE (f)-[:RELATED_TO]->(d)
            RETURN f
            """
            self.client.execute_write(fact_cypher, {
                "decision_id": decision_id,
                "outcome_id": outcome.id,
                "fact_id": fact_id,
                "content": new_lesson,
                "valid_from": datetime.now(timezone.utc).isoformat()
            })
            new_fact = MemoryFact(
                id=fact_id,
                content=new_lesson,
                memory_type=MemoryType.PROCEDURAL,
                status=FactStatus.ACTIVE
            )

        return outcome, new_fact

    def supersede_fact(self, old_fact_id: str, new_fact_content: str, reason: str) -> MemoryFact:
        """
        Explicitly supersede an existing fact without deleting it.
        Creates (:MemoryFact {SUPERSEDES})-[:SUPERSEDES]->(old:MemoryFact)
        Marks old fact status as 'superseded' and sets valid_to timestamp.
        """
        new_fact_id = f"FACT-SUP-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        cypher = """
        MATCH (old:MemoryFact {id: $old_fact_id})
        SET old.status = 'superseded', old.valid_to = $now, old.superseded_by = $new_fact_id
        CREATE (new_f:MemoryFact {
            id: $new_fact_id,
            content: $content,
            memory_type: old.memory_type,
            valid_from: $now,
            status: 'active',
            service: old.service,
            confidence: 1.0,
            supersession_reason: $reason
        })
        CREATE (new_f)-[:SUPERSEDES]->(old)
        RETURN new_f
        """
        params = {
            "old_fact_id": old_fact_id,
            "new_fact_id": new_fact_id,
            "content": new_fact_content,
            "now": now,
            "reason": reason
        }
        self.client.execute_write(cypher, params)
        return MemoryFact(id=new_fact_id, content=new_fact_content, memory_type=MemoryType.SEMANTIC, valid_from=now)

    def query_prior_incident_outcomes(self, service: str) -> Tuple[List[Dict[str, Any]], float]:
        """
        Multi-hop Cypher query: Retrieve past incidents, attempted actions, verified outcomes, and lessons.
        """
        cypher = """
        MATCH (i:Incident {service: $service}) -[:HAS_EPISODE]->(e:Episode) -[:CONTAINS]->(o:Observation) -[:SUPPORTS]->(f:MemoryFact)
        MATCH (f)-[:RELATED_TO]->(d:Decision) -[:RESULTED_IN]->(out:Outcome)
        RETURN 
            i.id AS incident_id,
            i.created_at AS incident_created_at,
            o.claim AS observation,
            f.id AS fact_id,
            f.content AS lesson,
            d.id AS decision_id,
            d.action AS action,
            d.rationale AS rationale,
            out.id AS outcome_id,
            out.result AS outcome,
            out.details AS outcome_details,
            out.impact_level AS impact_level
        ORDER BY out.verified_at DESC
        LIMIT 10
        """
        return self.client.query(cypher, {"service": service})

    def query_service_topology_and_facts(self, service: str) -> Tuple[Dict[str, Any], float]:
        """
        Semantic Memory query: Retrieve current service configuration, dependencies, and active facts.
        """
        svc_cypher = """
        MATCH (s:Service {name: $service})
        OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Service)
        OPTIONAL MATCH (s)-[:HAS_FACT]->(f:MemoryFact {status: 'active'})
        RETURN 
            s.id AS service_id,
            s.name AS service_name,
            s.version AS version,
            s.cache_type AS cache_type,
            s.pool_size AS pool_size,
            s.timeout_ms AS timeout_ms,
            s.config_summary AS config_summary,
            collect(DISTINCT dep.name) AS dependencies,
            collect(DISTINCT {id: f.id, content: f.content, valid_from: f.valid_from}) AS active_facts
        """
        rows, ms = self.client.query(svc_cypher, {"service": service})
        if rows:
            return rows[0], ms
        return {}, ms

    def query_procedures(self) -> Tuple[List[Dict[str, Any]], float]:
        """
        Procedural Memory query: Retrieve standard operating procedures, preconditions, and risk levels.
        """
        cypher = """
        MATCH (p:Procedure)
        RETURN 
            p.id AS procedure_id,
            p.name AS name,
            p.preconditions AS preconditions,
            p.risk_level AS risk_level,
            p.failure_modes AS failure_modes
        ORDER BY p.risk_level DESC
        """
        return self.client.query(cypher)

    def get_full_graph_elements(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch all nodes and relationships for interactive graph visualization.
        """
        nodes_cypher = """
        MATCH (n)
        RETURN id(n) AS internal_id, labels(n)[0] AS label, properties(n) AS props
        """
        node_rows, _ = self.client.query(nodes_cypher)

        edges_cypher = """
        MATCH (src)-[r]->(tgt)
        RETURN id(src) AS source, id(tgt) AS target, type(r) AS rel_type, properties(r) AS props
        """
        edge_rows, _ = self.client.query(edges_cypher)

        nodes = []
        for r in node_rows:
            props = r.get("props", {})
            node_id = props.get("id", str(r.get("internal_id")))
            nodes.append({
                "id": str(r.get("internal_id")),
                "name": node_id,
                "label": r.get("label", "Node"),
                "properties": props
            })

        edges = []
        for r in edge_rows:
            edges.append({
                "source": str(r.get("source")),
                "target": str(r.get("target")),
                "label": r.get("rel_type", "RELATED_TO"),
                "properties": r.get("props", {})
            })

        return nodes, edges

memory_engine = MemoryEngine()
