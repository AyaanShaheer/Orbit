import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.db.client import db_client
from src.models.graph_nodes import Task, TaskStatus
from src.models.events import TaskClaimResult

logger = logging.getLogger("orbit.coordination.tasks")

class TaskManager:
    """
    Graph-backed task coordination runtime.
    Enforces optimistic concurrency version checks and ownership in FalkorDB
    to guarantee zero duplicate task claims under concurrent execution.
    """
    def __init__(self):
        self.client = db_client

    def create_task(self, task_id: str, incident_id: str, name: str, description: str = "") -> Task:
        """Create an unclaimed task node in FalkorDB with version = 1."""
        now = datetime.now(timezone.utc).isoformat()
        cypher = """
        MERGE (t:Task {id: $task_id})
        ON CREATE SET
            t.incident_id = $incident_id,
            t.name = $name,
            t.description = $description,
            t.status = 'unclaimed',
            t.version = 1,
            t.owner_id = 'none',
            t.created_at = $now,
            t.updated_at = $now
        WITH t
        OPTIONAL MATCH (i:Incident {id: $incident_id})
        FOREACH (_ IN CASE WHEN i IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i)-[:HAS_TASK]->(t)
        )
        RETURN t.id AS id, t.version AS version
        """
        params = {
            "incident_id": incident_id,
            "task_id": task_id,
            "name": name,
            "description": description,
            "now": now
        }
        self.client.execute_write(cypher, params)
        return Task(id=task_id, incident_id=incident_id, name=name, description=description, version=1, status=TaskStatus.UNCLAIMED)

    def claim_task(self, task_id: str, agent_id: str, expected_version: int = 1) -> TaskClaimResult:
        """
        Attempt to claim a task using optimistic version locking.
        Only succeeds if task status is 'unclaimed' and version matches expected_version.
        """
        now = datetime.now(timezone.utc).isoformat()
        claim_cypher = """
        MATCH (t:Task {id: $task_id})
        MATCH (a:Agent {id: $agent_id})
        WHERE t.version = $expected_version AND t.status = 'unclaimed'
        SET t.status = 'claimed',
            t.owner_id = $agent_id,
            t.version = t.version + 1,
            t.updated_at = $now
        MERGE (a)-[:OWNS]->(t)
        RETURN t.id AS id, t.owner_id AS owner, t.version AS new_version
        """
        params = {
            "task_id": task_id,
            "agent_id": agent_id,
            "expected_version": expected_version,
            "now": now
        }
        rows, _ = self.client.query(claim_cypher, params)
        if rows:
            new_version = rows[0]["new_version"]
            logger.info(f"Task '{task_id}' successfully claimed by '{agent_id}' (v{new_version})")
            return TaskClaimResult(
                task_id=task_id,
                agent_id=agent_id,
                claimed=True,
                version_observed=expected_version,
                new_version=new_version
            )
        else:
            # Query current task state to return precise collision diagnostic
            check_cypher = "MATCH (t:Task {id: $task_id}) RETURN t.version AS version, t.owner_id AS owner, t.status AS status"
            check_rows, _ = self.client.query(check_cypher, {"task_id": task_id})
            if check_rows:
                curr_v = check_rows[0].get("version", 0)
                curr_owner = check_rows[0].get("owner", "unknown")
                curr_status = check_rows[0].get("status", "unknown")
                msg = f"Task claim conflict: expected version {expected_version}, but task is already '{curr_status}' (v{curr_v}) owned by '{curr_owner}'."
            else:
                msg = f"Task '{task_id}' not found."

            logger.warning(f"Task claim failed for '{agent_id}' on '{task_id}': {msg}")
            return TaskClaimResult(
                task_id=task_id,
                agent_id=agent_id,
                claimed=False,
                version_observed=expected_version,
                new_version=-1,
                error_message=msg
            )

    def complete_task(self, task_id: str, agent_id: str) -> bool:
        """Mark a claimed task as completed by its owner."""
        cypher = """
        MATCH (t:Task {id: $task_id, owner_id: $agent_id, status: 'claimed'})
        SET t.status = 'completed', t.updated_at = $now
        RETURN t.id AS id
        """
        rows, _ = self.client.query(cypher, {
            "task_id": task_id,
            "agent_id": agent_id,
            "now": datetime.now(timezone.utc).isoformat()
        })
        return len(rows) > 0

    def list_tasks(self, incident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks with their ownership and version metadata."""
        if incident_id:
            cypher = """
            MATCH (i:Incident {id: $incident_id})-[:HAS_TASK]->(t:Task)
            RETURN t.id AS id, t.name AS name, t.status AS status, t.version AS version, t.owner_id AS owner_id, t.updated_at AS updated_at
            ORDER BY t.created_at ASC
            """
            rows, _ = self.client.query(cypher, {"incident_id": incident_id})
        else:
            cypher = """
            MATCH (t:Task)
            RETURN t.id AS id, t.incident_id AS incident_id, t.name AS name, t.status AS status, t.version AS version, t.owner_id AS owner_id, t.updated_at AS updated_at
            ORDER BY t.updated_at DESC
            """
            rows, _ = self.client.query(cypher)
        return rows

task_manager = TaskManager()
