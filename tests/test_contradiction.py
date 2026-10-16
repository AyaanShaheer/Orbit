import pytest
from src.memory.contradiction import contradiction_detector

def test_contradiction_detection_on_config_drift():
    historical_outcomes = [{
        "incident_id": "INC-2026-0901",
        "observation": "Redis standalone connection pool exhaustion observed at 98% saturation",
        "action": "Restart Redis cache instance immediately",
        "outcome": "failure",
        "impact_level": "increased",
        "outcome_details": "Cascading failure on core-postgres",
        "fact_id": "FACT-0901-LESSON",
        "lesson": "Do not restart cache tier without verifying saturation preconditions"
    }]

    systems_facts = {
        "service_name": "checkout-service",
        "version": "2.4.0",
        "cache_type": "redis_cluster",
        "pool_size": 64
    }

    conflicts = contradiction_detector.check_hypothesis_conflicts(
        service="checkout-service",
        investigator_claims=["Historical checkout timeouts were associated with Redis exhaustion."],
        systems_facts=systems_facts,
        historical_outcomes=historical_outcomes,
        proposed_action="Restart Redis cache instance"
    )

    assert len(conflicts) == 2, "Expected both architectural drift and safety precondition conflicts"
    assert any(c.resolution == "differentiated_by_version" for c in conflicts)
    assert any(c.resolution == "precondition_enforced" for c in conflicts)
    for c in conflicts:
        assert len(c.supporting_graph_path) > 0
