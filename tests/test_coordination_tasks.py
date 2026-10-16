import pytest
import uuid
from src.coordination.task_manager import task_manager

def test_optimistic_task_claiming():
    task_id = f"test-task-{uuid.uuid4().hex[:6]}"
    task = task_manager.create_task(task_id, "INC-TEST-01", "Diagnostic Task", "Run connection inspection")
    assert task.status == "unclaimed"
    assert task.version == 1

    # First agent claims successfully
    res1 = task_manager.claim_task(task_id, "agent-systems", expected_version=1)
    assert res1.claimed is True
    assert res1.new_version == 2

    # Second agent attempts to claim the same task with version 1 -> Must be REJECTED!
    res2 = task_manager.claim_task(task_id, "agent-investigator", expected_version=1)
    assert res2.claimed is False
    assert "conflict" in res2.error_message.lower()

    # Complete the task
    completed = task_manager.complete_task(task_id, "agent-systems")
    assert completed is True
