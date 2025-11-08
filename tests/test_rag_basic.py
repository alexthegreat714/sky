"""
Basic RAG functionality tests (Phase 3 scaffold)

Will test:
- Index loading
- Query execution
- Similarity scoring
- Source document retrieval
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag import rag_loader


def test_load_index():
    """Test that RAG index can be loaded"""
    index = rag_loader.load_index()
    # Phase 3 scaffold: expect None for now
    assert index is None, "Phase 3 scaffold should return None"


def test_query_index():
    """Test basic RAG query"""
    result = rag_loader.query_index("What can Sky do?", k=3)

    # Phase 3 scaffold: expect empty results
    assert "matches" in result
    assert "source_docs" in result
    assert result["matches"] == []
    assert result["source_docs"] == []


def test_query_with_different_k():
    """Test RAG query with different k values"""
    for k in [1, 3, 5, 10]:
        result = rag_loader.query_index("Test query", k=k)
        assert isinstance(result, dict)
        assert "matches" in result


if __name__ == "__main__":
    print("Running RAG basic tests...")
    test_load_index()
    print("✓ test_load_index passed")

    test_query_index()
    print("✓ test_query_index passed")

    test_query_with_different_k()
    print("✓ test_query_with_different_k passed")

    print("\nAll RAG basic tests passed! (Phase 3 scaffold)")
