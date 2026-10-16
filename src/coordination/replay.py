import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from src.models.events import MemoryReplaySnapshot, AgentTimelineStep, ContradictionItem
from src.models.graph_nodes import Decision
from src.db.client import db_client

logger = logging.getLogger("orbit.coordination.replay")

class MemoryReplayEngine:
    """
    Auditable Memory Replay Engine.
    Allows judges and operators to reconstruct the exact graph state at any decision point:
    what the system retrieved, which agents disagreed, what evidence changed the decision,
    and what was learned afterward.
    """
    def __init__(self):
        self.client = db_client
        self._replay_store: Dict[str, MemoryReplaySnapshot] = {}

    def capture_snapshot(
        self,
        incident_id: str,
        decision: Decision,
        timeline: List[AgentTimelineStep],
        contradictions: List[ContradictionItem]
    ) -> MemoryReplaySnapshot:
        # Fetch active facts at decision time
        active_facts_cypher = """
        MATCH (f:MemoryFact {status: 'active'})
        RETURN f.id AS id, f.content AS content, f.memory_type AS type, f.valid_from AS valid_from
        """
        fact_rows, _ = self.client.query(active_facts_cypher)

        disagreements = []
        for c in contradictions:
            disagreements.append({
                "agent": c.new_source_agent,
                "disputed_prior_fact": c.prior_fact_content,
                "new_claim": c.new_claim,
                "conflict_reason": c.reason,
                "resolution": c.resolution
            })

        evidence_path = []
        for c in contradictions:
            for p in c.supporting_graph_path:
                evidence_path.append({"path_segment": p})

        snapshot = MemoryReplaySnapshot(
            incident_id=incident_id,
            decision_id=decision.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            active_facts_at_decision=fact_rows,
            agent_disagreements=disagreements,
            critical_evidence_path=evidence_path,
            chosen_action=decision.action,
            rationale=decision.rationale
        )

        self._replay_store[incident_id] = snapshot
        return snapshot

    def get_snapshot(self, incident_id: str) -> Optional[MemoryReplaySnapshot]:
        return self._replay_store.get(incident_id)

    def attach_lesson_learned(self, incident_id: str, lesson: str):
        if incident_id in self._replay_store:
            self._replay_store[incident_id].lesson_learned_afterward = lesson

replay_engine = MemoryReplayEngine()
