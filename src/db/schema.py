import logging
from typing import Dict, Any, List
from src.db.client import db_client

logger = logging.getLogger("orbit.schema")

INDEX_CYPHER_QUERIES = [
    "CREATE INDEX ON :Incident(id)",
    "CREATE INDEX ON :Incident(service)",
    "CREATE INDEX ON :Episode(id)",
    "CREATE INDEX ON :Observation(id)",
    "CREATE INDEX ON :MemoryFact(id)",
    "CREATE INDEX ON :MemoryFact(status)",
    "CREATE INDEX ON :MemoryFact(service)",
    "CREATE INDEX ON :Decision(id)",
    "CREATE INDEX ON :Task(id)",
    "CREATE INDEX ON :Service(id)",
    "CREATE INDEX ON :Procedure(name)",
    "CREATE INDEX ON :Outcome(result)",
]

def init_schema() -> bool:
    """
    Initialize indices in FalkorDB using standard FalkorDB Cypher syntax.
    """
    if not db_client.is_connected:
        logger.warning("FalkorDB is not connected. Skipping index creation.")
        return False

    success_count = 0
    for query in INDEX_CYPHER_QUERIES:
        try:
            db_client.execute_write(query)
            success_count += 1
        except Exception as e:
            # If index already exists or is supported, continue gracefully
            if "already exists" in str(e).lower() or "redundant" in str(e).lower():
                success_count += 1
            else:
                logger.debug(f"Index creation note for '{query}': {e}")

    logger.info(f"Schema initialized. {success_count}/{len(INDEX_CYPHER_QUERIES)} indices verified.")
    return True

def get_graph_statistics() -> Dict[str, Any]:
    """
    Inspect FalkorDB to return exact node and relationship counts.
    """
    if not db_client.is_connected:
        return {
            "connected": False,
            "node_counts": {},
            "edge_counts": {},
            "total_nodes": 0,
            "total_edges": 0
        }

    labels = ["Agent", "Incident", "Episode", "Observation", "MemoryFact", "Decision", "Task", "Outcome", "Procedure", "Service"]
    node_counts = {}
    total_nodes = 0
    for label in labels:
        try:
            rows, _ = db_client.query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
            count = rows[0]["cnt"] if rows else 0
            node_counts[label] = count
            total_nodes += count
        except Exception as e:
            node_counts[label] = 0

    rel_types = ["OWNS", "CONTRIBUTED", "CONTAINS", "SUPPORTS", "CONTRADICTS", "BASED_ON", "USED_PROCEDURE", "RESULTED_IN", "SUPERSEDES", "AFFECTS", "HAS_EPISODE", "RELATED_TO", "DEPENDS_ON", "HAS_FACT"]
    edge_counts = {}
    total_edges = 0
    for rel in rel_types:
        try:
            rows, _ = db_client.query(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt")
            count = rows[0]["cnt"] if rows else 0
            edge_counts[rel] = count
            total_edges += count
        except Exception as e:
            edge_counts[rel] = 0

    return {
        "connected": True,
        "node_counts": node_counts,
        "edge_counts": edge_counts,
        "total_nodes": total_nodes,
        "total_edges": total_edges
    }
