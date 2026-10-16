import pytest
from src.memory.engine import memory_engine
from src.db.client import db_client

def test_memory_fact_superseding_preserves_history():
    # Retrieve an active fact
    rows, _ = db_client.query("MATCH (f:MemoryFact {status: 'active'}) RETURN f.id AS id, f.content AS content LIMIT 1")
    assert len(rows) > 0
    old_id = rows[0]["id"]

    new_content = "Updated operational fact: checkout cache layer utilizes Redis Cluster with auto-failover."
    new_fact = memory_engine.supersede_fact(
        old_fact_id=old_id,
        new_fact_content=new_content,
        reason="Infrastructure upgrade from standalone to cluster"
    )

    assert new_fact.id != old_id
    assert new_fact.content == new_content

    # Verify old fact still exists in FalkorDB with status = 'superseded' (NEVER deleted!)
    old_rows, _ = db_client.query(f"MATCH (f:MemoryFact {{id: '{old_id}'}}) RETURN f.status AS status, f.superseded_by AS sup")
    assert len(old_rows) == 1
    assert old_rows[0]["status"] == "superseded"
    assert old_rows[0]["sup"] == new_fact.id

    # Verify SUPERSEDES relationship in FalkorDB
    rel_rows, _ = db_client.query(f"MATCH (new:MemoryFact {{id: '{new_fact.id}'}})-[r:SUPERSEDES]->(old:MemoryFact {{id: '{old_id}'}}) RETURN r")
    assert len(rel_rows) == 1
