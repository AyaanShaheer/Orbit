import pytest
from src.coordination.state_machine import coordination_pipeline
from src.simulation.runner import scenario_runner

def test_full_incident_triage_pipeline():
    incident_id = "INC-E2E-TEST-01"
    response = coordination_pipeline.run_investigation(
        incident_id=incident_id,
        service="checkout-service",
        severity="critical",
        description="End-to-end multi-agent verification run"
    )

    assert response.incident_id == incident_id
    assert response.status == "resolved"
    assert len(response.timeline) == 4, "Must have 4 coordinated agent steps"
    
    # Check agent roles in timeline
    roles = [step.agent_role for step in response.timeline]
    assert roles == ["investigator", "systems", "policy", "coordinator"]

    # Decision should enforce safe precondition inspection over blind restart
    assert "PROC-INSPECT-POOL" in response.decision.action
    assert len(response.contradictions) > 0
    assert response.execution_time_ms < 500.0, "Multi-agent graph triage should execute under 500ms"

def test_all_four_hackathon_demo_scenes():
    # Scene 1
    s1 = scenario_runner.run_scene_1_cold_start()
    assert s1["session_conversational_history"] == "NONE (Cold Start)"
    assert s1["falkordb_memories_retrieved"] > 0

    # Scene 2
    s2 = scenario_runner.run_scene_2_agents_disagree()
    assert len(s2["contradictions_detected"]) > 0

    # Scene 3
    s3 = scenario_runner.run_scene_3_cross_session_learning()
    assert s3["learned_adaptation_proven"] is True

    # Scene 4
    s4 = scenario_runner.run_scene_4_break_memory_and_concurrency()
    assert s4["duplicate_claims_prevented"] is True

def test_comparative_baseline():
    comp = scenario_runner.run_comparison()
    data = comp["comparison"]
    assert data["without_orbit"]["awareness_of_config_change"] is False
    assert data["with_orbit"]["awareness_of_config_change"] is True
