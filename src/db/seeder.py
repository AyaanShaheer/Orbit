import logging
from typing import Dict, Any, List
from src.db.client import db_client
from src.db.schema import init_schema

logger = logging.getLogger("orbit.seeder")

SEED_QUERIES = [
    # 1. Services
    """
    MERGE (s1:Service {id: 'svc-checkout', name: 'checkout-service', version: '2.4.0', cache_type: 'redis_cluster', pool_size: 64, timeout_ms: 500, config_summary: 'Redis Cluster multi-node with circuit breaker active'})
    MERGE (s2:Service {id: 'svc-cart', name: 'cart-service', version: '1.8.0', cache_type: 'redis_standalone', pool_size: 20, timeout_ms: 1000, config_summary: 'Redis standalone cache'})
    MERGE (s3:Service {id: 'svc-postgres', name: 'core-postgres', version: '15.4', cache_type: 'none', pool_size: 100, timeout_ms: 5000, config_summary: 'Primary relational persistence store'})
    MERGE (s1)-[:DEPENDS_ON]->(s2)
    MERGE (s1)-[:DEPENDS_ON]->(s3)
    """,

    # 2. Historical Incident INC-2026-0901
    """
    MATCH (s1:Service {id: 'svc-checkout'})
    MERGE (i1:Incident {
        id: 'INC-2026-0901',
        service: 'checkout-service',
        severity: 'critical',
        created_at: '2026-09-01T14:22:00Z',
        status: 'resolved',
        description: 'P99 checkout latency spiked to 8500ms during flash sale'
    })
    MERGE (i1)-[:AFFECTS]->(s1)
    MERGE (e1:Episode {
        id: 'EP-0901',
        session_id: 'sess-0901-investigation',
        incident_id: 'INC-2026-0901',
        started_at: '2026-09-01T14:23:00Z',
        ended_at: '2026-09-01T14:55:00Z',
        status: 'closed'
    })
    MERGE (i1)-[:HAS_EPISODE]->(e1)
    MERGE (o1:Observation {
        id: 'OBS-0901-1',
        claim: 'Redis standalone connection pool exhaustion observed at 98% saturation with 10/10 active connections locked',
        source_id: 'agent-investigator',
        observed_at: '2026-09-01T14:25:00Z',
        confidence: 0.96
    })
    MERGE (e1)-[:CONTAINS]->(o1)
    MERGE (f1:MemoryFact {
        id: 'FACT-0901-LESSON',
        content: 'Do NOT restart cache tier without verifying saturation preconditions; cold restart causes dogpile stampede on core-postgres',
        memory_type: 'procedural',
        valid_from: '2026-09-01T15:00:00Z',
        status: 'active',
        service: 'checkout-service',
        confidence: 0.98
    })
    MERGE (o1)-[:SUPPORTS]->(f1)
    MERGE (d1:Decision {
        id: 'DEC-0901-1',
        incident_id: 'INC-2026-0901',
        action: 'Restart Redis cache instance immediately',
        rationale: 'Hypothesized that stale connection leaks could be cleared by process reboot',
        created_at: '2026-09-01T14:30:00Z',
        recommended_by: 'coordinator-legacy',
        status: 'executed'
    })
    MERGE (d1)-[:BASED_ON]->(o1)
    MERGE (f1)-[:RELATED_TO]->(d1)
    MERGE (out1:Outcome {
        id: 'OUT-0901-1',
        decision_id: 'DEC-0901-1',
        result: 'failure',
        verified_at: '2026-09-01T14:40:00Z',
        details: 'Immediate cascading failure: 10,000 in-flight requests dropped, triggering simultaneous stampede on primary PostgreSQL, worsening latency to 18000ms',
        impact_level: 'increased'
    })
    MERGE (d1)-[:RESULTED_IN]->(out1)
    """,

    # 3. Procedures
    """
    MERGE (p1:Procedure {
        id: 'PROC-REDIS-RESTART',
        name: 'Cache Cluster Restart',
        preconditions: '1. Verify connection saturation < 70%. 2. Confirm read-replica availability. 3. Gracefully drain active connection leases.',
        risk_level: 'critical',
        failure_modes: 'Cascading database stampede, cache penetration storm, unrecoverable query latency spikes'
    })
    MERGE (p2:Procedure {
        id: 'PROC-INSPECT-POOL',
        name: 'Connection Pool & Saturation Telemetry Check',
        preconditions: 'None. Read-only diagnostic query.',
        risk_level: 'low',
        failure_modes: 'None'
    })
    MERGE (p3:Procedure {
        id: 'PROC-DRAIN-AND-SCALE',
        name: 'Dynamic Pool Expansion & Lease Drain',
        preconditions: 'Available host memory headroom > 25%',
        risk_level: 'medium',
        failure_modes: 'Temporary socket reconfiguration delay'
    })
    """,

    # 4. Connect Decision to Procedure
    """
    MATCH (d1:Decision {id: 'DEC-0901-1'})
    MATCH (p1:Procedure {id: 'PROC-REDIS-RESTART'})
    MERGE (d1)-[:USED_PROCEDURE]->(p1)
    """,

    # 5. Semantic Fact: System Configuration Shift
    """
    MATCH (s1:Service {id: 'svc-checkout'})
    MERGE (f_sem1:MemoryFact {
        id: 'FACT-SEM-CONFIG-V2',
        content: 'Checkout service v2.4.0 operates on Redis Cluster with 64 connections, automated circuit breaker, and isolated shards, replacing legacy v1.2 standalone Redis.',
        memory_type: 'semantic',
        valid_from: '2026-10-01T00:00:00Z',
        status: 'active',
        service: 'checkout-service',
        confidence: 1.0
    })
    MERGE (s1)-[:HAS_FACT]->(f_sem1)
    """,

    # 6. Agents
    """
    MERGE (ag1:Agent {id: 'agent-investigator', role: 'investigator', name: 'Investigator Agent', status: 'idle', description: 'Episodic memory specialist: retrieves historical incidents, past hypotheses, and failure outcomes'})
    MERGE (ag2:Agent {id: 'agent-systems', role: 'systems', name: 'Systems Agent', status: 'idle', description: 'Semantic memory specialist: traverses live dependency topology and detects configuration shifts'})
    MERGE (ag3:Agent {id: 'agent-policy', role: 'policy', name: 'Policy Agent', status: 'idle', description: 'Procedural memory specialist: retrieves recovery procedures, precondition checks, and past blast radiuses'})
    MERGE (ag4:Agent {id: 'agent-coordinator', role: 'coordinator', name: 'Coordinator Agent', status: 'idle', description: 'Belief integration specialist: reconciles conflicting claims, enforces evidence provenance, and commits verified outcomes'})
    """
]

def seed_database(drop_existing: bool = True) -> Dict[str, Any]:
    """
    Seed FalkorDB with the initial incident, services, procedures, and memory facts.
    """
    if not db_client.is_connected:
        logger.error("Cannot seed: FalkorDB is not connected.")
        return {"success": False, "error": "FalkorDB not connected"}

    if drop_existing:
        logger.info("Dropping existing graph for fresh clean seed...")
        db_client.drop_graph()

    # Re-init schema indices
    init_schema()

    total_time_ms = 0.0
    for idx, query in enumerate(SEED_QUERIES):
        try:
            elapsed = db_client.execute_write(query)
            total_time_ms += elapsed
        except Exception as e:
            logger.error(f"Error in seed step {idx + 1}: {e} | Query: {query}")
            return {"success": False, "error": str(e), "failed_step": idx + 1}

    logger.info(f"Database seeded successfully in {total_time_ms:.2f} ms.")
    return {
        "success": True,
        "seed_time_ms": total_time_ms,
        "message": "Graph successfully seeded with historical incidents, topology, procedures, and agent definitions."
    }
