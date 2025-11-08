"""
Tests for Sky Task Runner
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from sky.tasks.task_runner import TaskQueue, TaskScheduler

# Test fixtures
TEST_QUEUE_FILE = Path(__file__).parent / "test_queue.json"


@pytest.fixture
def clean_queue():
    """Clean test queue before and after tests"""
    if TEST_QUEUE_FILE.exists():
        TEST_QUEUE_FILE.unlink()
    yield
    if TEST_QUEUE_FILE.exists():
        TEST_QUEUE_FILE.unlink()


@pytest.fixture
def task_queue(clean_queue):
    """Create test task queue"""
    return TaskQueue(queue_file=TEST_QUEUE_FILE)


def test_queue_creation(task_queue):
    """Test queue file is created"""
    assert TEST_QUEUE_FILE.exists()


def test_add_task(task_queue):
    """Test adding a task"""
    task = {
        "name": "test_task",
        "schedule": "08:00",
        "action": "run_tool('test_tool')"
    }

    result = task_queue.add_task(task)
    assert result is True

    # Verify task was added
    tasks = task_queue.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "test_task"
    assert tasks[0]["enabled"] is True  # Default


def test_add_duplicate_task(task_queue):
    """Test adding duplicate task fails"""
    task = {"name": "duplicate", "action": "run_tool('test')"}

    assert task_queue.add_task(task) is True
    assert task_queue.add_task(task) is False  # Should fail


def test_add_invalid_task(task_queue):
    """Test adding invalid task fails"""
    # Missing required fields
    invalid_task = {"name": "invalid"}
    assert task_queue.add_task(invalid_task) is False


def test_get_task(task_queue):
    """Test retrieving task by name"""
    task = {"name": "find_me", "action": "run_tool('test')"}
    task_queue.add_task(task)

    found = task_queue.get_task("find_me")
    assert found is not None
    assert found["name"] == "find_me"

    not_found = task_queue.get_task("not_exist")
    assert not_found is None


def test_update_task(task_queue):
    """Test updating task"""
    task = {"name": "update_me", "action": "run_tool('test')", "schedule": "08:00"}
    task_queue.add_task(task)

    # Update schedule
    result = task_queue.update_task("update_me", {"schedule": "09:00"})
    assert result is True

    updated = task_queue.get_task("update_me")
    assert updated["schedule"] == "09:00"


def test_enable_disable_task(task_queue):
    """Test enabling and disabling tasks"""
    task = {"name": "toggle_me", "action": "run_tool('test')"}
    task_queue.add_task(task)

    # Disable
    assert task_queue.disable_task("toggle_me") is True
    disabled = task_queue.get_task("toggle_me")
    assert disabled["enabled"] is False

    # Enable
    assert task_queue.enable_task("toggle_me") is True
    enabled = task_queue.get_task("toggle_me")
    assert enabled["enabled"] is True


def test_remove_task(task_queue):
    """Test removing task"""
    task = {"name": "remove_me", "action": "run_tool('test')"}
    task_queue.add_task(task)

    assert task_queue.remove_task("remove_me") is True
    assert task_queue.get_task("remove_me") is None

    # Removing non-existent task should fail
    assert task_queue.remove_task("not_exist") is False


def test_scheduler_parse_schedule():
    """Test schedule parsing"""
    scheduler = TaskScheduler(None)

    # Valid schedules
    assert scheduler._parse_schedule("08:30") == (8, 30)
    assert scheduler._parse_schedule("00:00") == (0, 0)
    assert scheduler._parse_schedule("23:59") == (23, 59)

    # Invalid schedules
    assert scheduler._parse_schedule("25:00") is None
    assert scheduler._parse_schedule("08:60") is None
    assert scheduler._parse_schedule("invalid") is None
    assert scheduler._parse_schedule("8:30:00") is None
    assert scheduler._parse_schedule(None) is None


def test_scheduler_should_run(task_queue):
    """Test task should_run logic"""
    scheduler = TaskScheduler(task_queue)
    now = datetime.now()

    # Task scheduled for current time
    task_now = {
        "name": "run_now",
        "schedule": f"{now.hour:02d}:{now.minute:02d}",
        "enabled": True,
        "last_run": None,
        "action": "run_tool('test')"
    }
    assert scheduler._should_run(task_now, now) is True

    # Disabled task should not run
    task_disabled = {**task_now, "enabled": False}
    assert scheduler._should_run(task_disabled, now) is False

    # Task scheduled for different time
    different_hour = (now.hour + 1) % 24
    task_later = {
        "name": "run_later",
        "schedule": f"{different_hour:02d}:{now.minute:02d}",
        "enabled": True,
        "last_run": None,
        "action": "run_tool('test')"
    }
    assert scheduler._should_run(task_later, now) is False

    # Task with recent last_run should not run again
    task_recent = {
        "name": "ran_recently",
        "schedule": f"{now.hour:02d}:{now.minute:02d}",
        "enabled": True,
        "last_run": now.isoformat(),  # Just ran
        "action": "run_tool('test')"
    }
    assert scheduler._should_run(task_recent, now) is False


def test_list_tasks(task_queue):
    """Test listing all tasks"""
    tasks = [
        {"name": "task1", "action": "run_tool('test1')"},
        {"name": "task2", "action": "run_tool('test2')"},
        {"name": "task3", "action": "run_tool('test3')"}
    ]

    for task in tasks:
        task_queue.add_task(task)

    listed = task_queue.list_tasks()
    assert len(listed) == 3
    assert {t["name"] for t in listed} == {"task1", "task2", "task3"}


def test_queue_persistence(clean_queue):
    """Test queue persists across instances"""
    # Create queue and add task
    queue1 = TaskQueue(queue_file=TEST_QUEUE_FILE)
    queue1.add_task({"name": "persist_me", "action": "run_tool('test')"})

    # Create new queue instance and verify task exists
    queue2 = TaskQueue(queue_file=TEST_QUEUE_FILE)
    task = queue2.get_task("persist_me")
    assert task is not None
    assert task["name"] == "persist_me"


def test_empty_queue(task_queue):
    """Test operations on empty queue"""
    tasks = task_queue.list_tasks()
    assert tasks == []

    assert task_queue.get_task("nonexistent") is None
    assert task_queue.remove_task("nonexistent") is False
    assert task_queue.enable_task("nonexistent") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
