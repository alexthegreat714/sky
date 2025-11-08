"""
Tests for Sky Memory Inspector
"""
import pytest
import json
from pathlib import Path
from sky.memory.inspector import MemoryInspector

# Test fixtures
TEST_MEM_DIR = Path(__file__).parent / "test_memory"
TEST_ST_FILE = TEST_MEM_DIR / "short_term.jsonl"
TEST_LT_FILE = TEST_MEM_DIR / "long_term.jsonl"


@pytest.fixture
def clean_memory():
    """Clean test memory files before and after tests"""
    if TEST_MEM_DIR.exists():
        for f in TEST_MEM_DIR.glob("*.jsonl"):
            f.unlink()
        TEST_MEM_DIR.rmdir()
    yield
    if TEST_MEM_DIR.exists():
        for f in TEST_MEM_DIR.glob("*.jsonl"):
            f.unlink()
        TEST_MEM_DIR.rmdir()


@pytest.fixture
def inspector(clean_memory, monkeypatch):
    """Create test memory inspector with mocked paths"""
    # Patch the module-level paths
    import sky.memory.inspector as insp_module
    monkeypatch.setattr(insp_module, "MEM_DIR", TEST_MEM_DIR)
    monkeypatch.setattr(insp_module, "ST_FILE", TEST_ST_FILE)
    monkeypatch.setattr(insp_module, "LT_FILE", TEST_LT_FILE)

    # Also patch the inspector instance
    inspector = MemoryInspector()
    monkeypatch.setattr(inspector, "_get_file_path", lambda t: TEST_ST_FILE if t == "short" else TEST_LT_FILE)

    return inspector


def create_test_memory(file_path: Path, entries: list):
    """Helper to create test memory files"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def test_list_empty_memories(inspector):
    """Test listing empty memory store"""
    memories = inspector.list_memories(memory_type="short")
    assert memories == []


def test_list_memories(inspector):
    """Test listing memories"""
    # Create test memories
    test_entries = [
        {"ts": 1000, "type": "short", "content": "Memory 1", "importance": 0.5},
        {"ts": 2000, "type": "short", "content": "Memory 2", "importance": 0.7},
        {"ts": 3000, "type": "short", "content": "Memory 3", "importance": 0.9}
    ]
    create_test_memory(TEST_ST_FILE, test_entries)

    memories = inspector.list_memories(memory_type="short")

    assert len(memories) == 3
    assert all("id" in m for m in memories)
    assert all("line_number" in m for m in memories)
    assert memories[0]["content"] == "Memory 1"
    assert memories[1]["content"] == "Memory 2"
    assert memories[2]["content"] == "Memory 3"


def test_get_memory(inspector):
    """Test getting specific memory by ID"""
    test_entries = [
        {"ts": 1000, "type": "short", "content": "Find me", "importance": 0.5},
        {"ts": 2000, "type": "short", "content": "Not me", "importance": 0.6}
    ]
    create_test_memory(TEST_ST_FILE, test_entries)

    # List to get IDs
    memories = inspector.list_memories(memory_type="short")
    first_id = memories[0]["id"]

    # Get specific memory
    memory = inspector.get_memory(first_id, memory_type="short")
    assert memory is not None
    assert memory["content"] == "Find me"

    # Try non-existent ID
    not_found = inspector.get_memory("nonexistent", memory_type="short")
    assert not_found is None


def test_delete_memory(inspector):
    """Test deleting memory"""
    test_entries = [
        {"ts": 1000, "type": "short", "content": "Keep me", "importance": 0.5},
        {"ts": 2000, "type": "short", "content": "Delete me", "importance": 0.6},
        {"ts": 3000, "type": "short", "content": "Keep me too", "importance": 0.7}
    ]
    create_test_memory(TEST_ST_FILE, test_entries)

    # Get memory to delete
    memories = inspector.list_memories(memory_type="short")
    delete_id = memories[1]["id"]
    assert memories[1]["content"] == "Delete me"

    # Delete
    result = inspector.delete_memory(delete_id, memory_type="short")
    assert result["ok"] is True
    assert result["memory_id"] == delete_id
    assert "Delete me" in result["content"]

    # Verify deletion
    remaining = inspector.list_memories(memory_type="short")
    assert len(remaining) == 2
    assert all(m["content"] != "Delete me" for m in remaining)


def test_delete_nonexistent_memory(inspector):
    """Test deleting non-existent memory"""
    result = inspector.delete_memory("nonexistent", memory_type="short")
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_promote_memory(inspector):
    """Test promoting memory from short to long"""
    test_entries = [
        {"ts": 1000, "type": "short", "content": "Promote me", "importance": 0.5, "tags": ["test"]},
        {"ts": 2000, "type": "short", "content": "Stay short", "importance": 0.3}
    ]
    create_test_memory(TEST_ST_FILE, test_entries)

    # Get memory to promote
    memories = inspector.list_memories(memory_type="short")
    promote_id = memories[0]["id"]

    # Promote
    result = inspector.promote_memory(promote_id)
    assert result["ok"] is True
    assert result["memory_id"] == promote_id
    assert "Promote me" in result["content"]

    # Verify removed from short-term
    st_memories = inspector.list_memories(memory_type="short")
    assert len(st_memories) == 1
    assert st_memories[0]["content"] == "Stay short"

    # Verify added to long-term
    lt_memories = inspector.list_memories(memory_type="long")
    assert len(lt_memories) == 1
    assert lt_memories[0]["content"] == "Promote me"
    assert lt_memories[0]["type"] == "long"
    assert "promoted_at" in lt_memories[0]
    assert lt_memories[0]["importance"] >= 0.7  # Boosted to at least 0.7


def test_promote_nonexistent_memory(inspector):
    """Test promoting non-existent memory"""
    result = inspector.promote_memory("nonexistent")
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_promote_empty_content(inspector):
    """Test promoting memory with no content"""
    test_entries = [
        {"ts": 1000, "type": "short", "content": "", "importance": 0.5}
    ]
    create_test_memory(TEST_ST_FILE, test_entries)

    memories = inspector.list_memories(memory_type="short")
    promote_id = memories[0]["id"]

    result = inspector.promote_memory(promote_id)
    assert result["ok"] is False
    assert "no content" in result["error"].lower()


def test_get_stats(inspector):
    """Test getting memory statistics"""
    # Create test memories
    st_entries = [
        {"ts": 1000, "type": "short", "content": "Short 1"},
        {"ts": 2000, "type": "short", "content": "Short 2"}
    ]
    lt_entries = [
        {"ts": 3000, "type": "long", "content": "Long 1"},
        {"ts": 4000, "type": "long", "content": "Long 2"},
        {"ts": 5000, "type": "long", "content": "Long 3"}
    ]
    create_test_memory(TEST_ST_FILE, st_entries)
    create_test_memory(TEST_LT_FILE, lt_entries)

    stats = inspector.get_stats()

    assert stats["short_term"]["count"] == 2
    assert stats["long_term"]["count"] == 3
    assert "rag" in stats
    assert isinstance(stats["rag"]["enabled"], bool)


def test_memory_id_consistency(inspector):
    """Test that memory IDs are consistent across reads"""
    test_entries = [
        {"ts": 1000, "type": "short", "content": "Consistent ID test"}
    ]
    create_test_memory(TEST_ST_FILE, test_entries)

    # Read multiple times
    memories1 = inspector.list_memories(memory_type="short")
    memories2 = inspector.list_memories(memory_type="short")

    assert memories1[0]["id"] == memories2[0]["id"]


def test_list_long_term_memories(inspector):
    """Test listing long-term memories"""
    lt_entries = [
        {"ts": 1000, "type": "long", "content": "Long memory 1", "importance": 0.8},
        {"ts": 2000, "type": "long", "content": "Long memory 2", "importance": 0.9}
    ]
    create_test_memory(TEST_LT_FILE, lt_entries)

    memories = inspector.list_memories(memory_type="long")

    assert len(memories) == 2
    assert all(m["type"] == "long" for m in memories)


def test_delete_from_long_term(inspector):
    """Test deleting from long-term memory"""
    lt_entries = [
        {"ts": 1000, "type": "long", "content": "Delete from long", "importance": 0.8}
    ]
    create_test_memory(TEST_LT_FILE, lt_entries)

    memories = inspector.list_memories(memory_type="long")
    delete_id = memories[0]["id"]

    result = inspector.delete_memory(delete_id, memory_type="long")
    assert result["ok"] is True
    assert result["memory_type"] == "long"

    remaining = inspector.list_memories(memory_type="long")
    assert len(remaining) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
