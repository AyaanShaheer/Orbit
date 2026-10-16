import pytest
from src.db.client import db_client
from src.db.schema import get_graph_statistics
from src.db.seeder import seed_database

def test_falkordb_connection():
    assert db_client.is_connected, "FalkorDB client must be connected"
    rows, ms = db_client.query("RETURN 1 AS ping")
    assert len(rows) == 1
    assert rows[0]["ping"] == 1
    assert ms < 50.0, "Graph query latency should be well under 50ms"

def test_seed_and_graph_stats():
    seed_res = seed_database(drop_existing=True)
    assert seed_res["success"] is True

    stats = get_graph_statistics()
    assert stats["connected"] is True
    assert stats["node_counts"]["Agent"] == 4
    assert stats["node_counts"]["Incident"] >= 1
    assert stats["node_counts"]["Service"] >= 3
    assert stats["node_counts"]["Procedure"] >= 3
    assert stats["total_nodes"] >= 15
    assert stats["total_edges"] >= 10

def test_multihop_cypher_recall():
    cypher = """
    MATCH (i:Incident {service: 'checkout-service'}) -[:HAS_EPISODE]->(e:Episode) -[:CONTAINS]->(o:Observation) -[:SUPPORTS]->(f:MemoryFact)
    MATCH (f)-[:RELATED_TO]->(d:Decision) -[:RESULTED_IN]->(out:Outcome)
    WHERE out.result = 'failure'
    RETURN i.id AS incident_id, o.claim AS observation, f.content AS lesson, d.action AS action, out.result AS outcome
    """
    rows, ms = db_client.query(cypher)
    assert len(rows) >= 1
    assert rows[0]["incident_id"] == "INC-2026-0901"
    assert rows[0]["outcome"] == "failure"
    assert "restart" in rows[0]["action"].lower()
    assert ms < 100.0
