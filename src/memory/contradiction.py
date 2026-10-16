import logging
from typing import List, Dict, Any, Optional
from src.models.events import ContradictionItem
from src.memory.engine import memory_engine

logger = logging.getLogger("orbit.memory.contradiction")

class ContradictionDetector:
    """
    Evaluates agent hypotheses and observations against active graph memory,
    identifying historical mismatches, configuration drifts, and missing safety preconditions.
    """
    def __init__(self):
        self.engine = memory_engine

    def check_hypothesis_conflicts(
        self,
        service: str,
        investigator_claims: List[str],
        systems_facts: Dict[str, Any],
        historical_outcomes: List[Dict[str, Any]],
        proposed_action: Optional[str] = None
    ) -> List[ContradictionItem]:
        """
        Evaluate conflicting beliefs between:
        1. Investigator (Episodic recall of past Redis crash)
        2. Systems (Semantic verification of current v2.4 cluster topology)
        3. Policy (Procedural rules and precondition checks)
        """
        contradictions: List[ContradictionItem] = []

        # 1. Check Configuration Drift / Topology Mismatch
        current_version = systems_facts.get("version", "unknown")
        current_cache = systems_facts.get("cache_type", "unknown")
        current_pool = systems_facts.get("pool_size", 0)

        for hist in historical_outcomes:
            prior_lesson = hist.get("lesson", "")
            prior_action = hist.get("action", "")
            prior_outcome = hist.get("outcome", "")

            # If historical incident was Redis standalone exhaustion and current is cluster
            if "standalone" in hist.get("observation", "").lower() and "cluster" in current_cache.lower():
                contradictions.append(ContradictionItem(
                    prior_fact_id=hist.get("fact_id", "FACT-HIST"),
                    prior_fact_content=prior_lesson,
                    prior_service_version="v1.2.0 (Standalone Redis, pool=10)",
                    new_claim=f"Current {service} operates on {current_cache} (v{current_version}, pool={current_pool}) with circuit breaker.",
                    new_source_agent="agent-systems",
                    reason="Architectural drift: Historical incident root cause occurred on a standalone cache architecture with pool size 10. Current environment is a distributed multi-node cluster with pool size 64.",
                    resolution="differentiated_by_version",
                    supporting_graph_path=[
                        f"(:Incident {{id: '{hist.get('incident_id')}'}})-[:AFFECTS]->(:Service {{version: '1.2.0'}})",
                        f"(:Service {{id: 'svc-checkout', version: '{current_version}'}})-[:HAS_FACT]->(:MemoryFact {{content: '{current_cache}'}})"
                    ]
                ))

            # If proposed action matches a prior failure
            if proposed_action and ("restart" in proposed_action.lower() and "restart" in prior_action.lower()):
                if prior_outcome == "failure":
                    contradictions.append(ContradictionItem(
                        prior_fact_id=hist.get("fact_id", "FACT-SAFETY"),
                        prior_fact_content=f"Prior attempted action '{prior_action}' failed with impact '{hist.get('impact_level', 'increased')}': {hist.get('outcome_details', '')}",
                        prior_service_version="v1.2.0",
                        new_claim=f"Proposed action: '{proposed_action}'",
                        new_source_agent="agent-investigator",
                        reason="Precondition violation & Blast radius danger: Restarting the cache tier without verifying saturation saturation leases causes immediate cold dogpile stampede on primary PostgreSQL.",
                        resolution="precondition_enforced",
                        supporting_graph_path=[
                            f"(:Decision {{action: '{prior_action}'}})-[:RESULTED_IN]->(:Outcome {{result: 'failure'}})",
                            f"(:Procedure {{id: 'PROC-REDIS-RESTART'}})-[:REQUIRES]->(:Precondition {{name: 'saturation < 70%'}})"
                        ]
                    ))

        return contradictions

contradiction_detector = ContradictionDetector()
