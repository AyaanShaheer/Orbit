import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.db.client import db_client
from src.db.schema import get_graph_statistics
from src.db.seeder import seed_database
from src.coordination.state_machine import coordination_pipeline
from src.coordination.task_manager import task_manager
from src.coordination.replay import replay_engine
from src.memory.engine import memory_engine
from src.simulation.runner import scenario_runner
from src.models.api import (
    IncidentInvestigationRequest, InvestigationResponse, RecordOutcomeRequest,
    TaskClaimRequest, SystemStatsResponse
)
from src.models.graph_nodes import Outcome, OutcomeResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("orbit.api")

app = FastAPI(
    title="ORBIT — Operational Recall & Belief Integration for Teams",
    description="FalkorDB Authoritative Memory & Coordination Runtime for AI Incident Agents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "system": "ORBIT",
        "description": "Operational Recall & Belief Integration for Teams",
        "status": "online",
        "falkordb_connected": db_client.is_connected,
        "docs_url": "/docs"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy" if db_client.is_connected else "degraded",
        "falkordb_connected": db_client.is_connected,
        "falkordb_host": settings.falkordb_host,
        "falkordb_port": settings.falkordb_port
    }

@app.post("/api/seed")
def seed_graph(drop_existing: bool = Query(True)):
    """Reset and seed FalkorDB with synthetic incidents, topology, procedures, and agents."""
    return seed_database(drop_existing=drop_existing)

@app.get("/api/graph/stats")
def graph_stats():
    """Retrieve node and edge counts directly from FalkorDB."""
    return get_graph_statistics()

@app.get("/api/graph/elements")
def graph_elements():
    """Retrieve full node and edge list for interactive graph rendering."""
    nodes, edges = memory_engine.get_full_graph_elements()
    return {"nodes": nodes, "edges": edges}

@app.post("/api/investigate", response_model=InvestigationResponse)
def investigate_incident(req: IncidentInvestigationRequest):
    """Run full multi-agent triage: Investigator -> Systems -> Policy -> Coordinator."""
    try:
        res = coordination_pipeline.run_investigation(
            incident_id=req.incident_id,
            service=req.service,
            severity=req.severity,
            description=req.description
        )
        replay_engine.capture_snapshot(req.incident_id, res.decision, res.timeline, res.contradictions)
        return res
    except Exception as e:
        logger.error(f"Investigation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/outcome")
def record_outcome(req: RecordOutcomeRequest):
    """Record verified outcome and update graph memory with new lesson."""
    outcome = Outcome(
        id=f"OUT-{req.decision_id}",
        decision_id=req.decision_id,
        result=OutcomeResult(req.result),
        details=req.details,
        impact_level=req.impact_level
    )
    new_lesson = f"Verified lesson from incident {req.incident_id}: {req.details}"
    saved_outcome, new_fact = memory_engine.record_outcome(outcome, req.decision_id, new_lesson=new_lesson)
    replay_engine.attach_lesson_learned(req.incident_id, new_lesson)
    return {
        "success": True,
        "outcome": saved_outcome.model_dump(),
        "new_fact_created": new_fact.model_dump() if new_fact else None
    }

@app.post("/api/tasks/claim")
def claim_task(req: TaskClaimRequest):
    """Attempt optimistic task claim with version check."""
    res = task_manager.claim_task(req.task_id, req.agent_id, req.expected_version)
    return res.model_dump()

@app.get("/api/replay/{incident_id}")
def get_replay_snapshot(incident_id: str):
    """Retrieve auditable memory replay snapshot for an incident decision."""
    snapshot = replay_engine.get_snapshot(incident_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Replay snapshot not found for incident")
    return snapshot.model_dump()

@app.get("/api/scenarios/{scene_id}")
def run_scenario(scene_id: str):
    """Execute a predefined Hackathon demonstration scene."""
    if scene_id == "scene_1":
        return scenario_runner.run_scene_1_cold_start()
    elif scene_id == "scene_2":
        return scenario_runner.run_scene_2_agents_disagree()
    elif scene_id == "scene_3":
        return scenario_runner.run_scene_3_cross_session_learning()
    elif scene_id == "scene_4":
        return scenario_runner.run_scene_4_break_memory_and_concurrency()
    else:
        raise HTTPException(status_code=404, detail="Scenario not found. Valid: scene_1, scene_2, scene_3, scene_4")

@app.get("/api/comparison")
def get_comparison():
    """Run side-by-side comparison: Without Graph vs With ORBIT."""
    return scenario_runner.run_comparison()
