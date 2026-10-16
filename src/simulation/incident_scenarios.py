from typing import Dict, Any, List
from pydantic import BaseModel

class DemoScenario(BaseModel):
    id: str
    title: str
    description: str
    incident_id: str
    service: str
    severity: str
    details: str

DEMO_SCENARIOS = {
    "scene_1_cold_start": DemoScenario(
        id="scene_1_cold_start",
        title="Scene 1: The Cold Start",
        description="Fresh session with zero conversational chat history. Demonstrates FalkorDB persistent memory retrieval across sessions.",
        incident_id="INC-2026-1016-01",
        service="checkout-service",
        severity="critical",
        details="P99 checkout latency spiked to 9200ms. Zero conversation context exists in agent runtime."
    ),
    "scene_2_agents_disagree": DemoScenario(
        id="scene_2_agents_disagree",
        title="Scene 2: Agents Disagree & Reconcile",
        description="Investigator proposes historical Redis cause; Systems spots v2.4 cluster migration; Policy flags restart cascading risk. Coordinator resolves conflict.",
        incident_id="INC-2026-1016-02",
        service="checkout-service",
        severity="critical",
        details="Checkout latency degradation. Agents formulate competing hypotheses based on episodic vs semantic vs procedural memory."
    ),
    "scene_3_cross_session_learning": DemoScenario(
        id="scene_3_cross_session_learning",
        title="Scene 3: Cross-Session Learning (Lesson Survived)",
        description="Record verified outcome from prior inspection, update graph memory, start a new session, and prove that ORBIT adapts its recommendation.",
        incident_id="INC-2026-1016-03",
        service="checkout-service",
        severity="high",
        details="Re-testing checkout service with updated procedural fact from previously verified diagnostic outcome."
    ),
    "scene_4_break_memory": DemoScenario(
        id="scene_4_break_memory",
        title="Scene 4: Break the Memory (Contradiction & Concurrency)",
        description="Inject conflicting stale fact and launch concurrent task claims. Shows conflict flagged, stale work rejected, and version locks preventing race conditions.",
        incident_id="INC-2026-1016-04",
        service="checkout-service",
        severity="critical",
        details="Stale fact injection & simultaneous task claim collision test."
    )
}
