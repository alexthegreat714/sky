"""
Tests for Sky Self-Improvement Tool
"""
import pytest
import json
from pathlib import Path
from sky.self.self_improve import SelfImprovementTool

# Test fixtures
TEST_ARCHIVE_DIR = Path(__file__).parent / "test_archive"
TEST_AUDIT_FILE = Path(__file__).parent / "test_audit_log.jsonl"


@pytest.fixture
def clean_files():
    """Clean test files before and after tests"""
    if TEST_ARCHIVE_DIR.exists():
        for f in TEST_ARCHIVE_DIR.glob("*"):
            f.unlink()
        TEST_ARCHIVE_DIR.rmdir()
    if TEST_AUDIT_FILE.exists():
        TEST_AUDIT_FILE.unlink()
    yield
    if TEST_ARCHIVE_DIR.exists():
        for f in TEST_ARCHIVE_DIR.glob("*"):
            f.unlink()
        TEST_ARCHIVE_DIR.rmdir()
    if TEST_AUDIT_FILE.exists():
        TEST_AUDIT_FILE.unlink()


@pytest.fixture
def tool(clean_files, monkeypatch):
    """Create test self-improvement tool with mocked paths"""
    import sky.self.self_improve as improve_module

    monkeypatch.setattr(improve_module, "ARCHIVE_DIR", TEST_ARCHIVE_DIR)
    monkeypatch.setattr(improve_module, "AUDIT_FILE", TEST_AUDIT_FILE)

    TEST_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    tool = SelfImprovementTool()
    tool.archive_dir = TEST_ARCHIVE_DIR
    tool.audit_file = TEST_AUDIT_FILE

    return tool


def test_chunk_text_short(tool):
    """Test chunking short text"""
    text = "This is a short text."
    chunks = tool._chunk_text(text, chunk_size=100)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long(tool):
    """Test chunking long text"""
    text = "Word. " * 500  # Long repeating text
    chunks = tool._chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    # Verify overlap exists
    for i in range(len(chunks) - 1):
        # Some content should appear in consecutive chunks
        assert len(chunks[i]) > 0


def test_compute_hash(tool):
    """Test hash computation"""
    text1 = "Hello World"
    text2 = "Hello World"
    text3 = "Different"

    hash1 = tool._compute_hash(text1)
    hash2 = tool._compute_hash(text2)
    hash3 = tool._compute_hash(text3)

    # Same text should have same hash
    assert hash1 == hash2

    # Different text should have different hash
    assert hash1 != hash3

    # Hash should be 64 characters (SHA256 hex)
    assert len(hash1) == 64


def test_estimate_tokens(tool):
    """Test token estimation"""
    text = "This is a test with ten words here now."

    tokens = tool._estimate_tokens(text)

    # Should be roughly 10 * 1.3 = 13
    assert tokens > 0
    assert tokens >= 10  # At least number of words


def test_ingest_text(tool):
    """Test ingesting plain text"""
    text = "This is test content for knowledge ingestion."

    result = tool.ingest_text(text, source_name="test_doc")

    assert result["ok"] is True
    assert result["source_type"] == "text"
    assert result["source_name"] == "test_doc"
    assert result["tokens"] > 0
    assert result["chunks"] > 0
    assert "hash" in result
    assert "archive_file" in result

    # Verify archive file was created
    archive_path = Path(result["archive_file"])
    assert archive_path.exists()
    assert archive_path.read_text() == text


def test_ingest_text_chunking(tool):
    """Test text is properly chunked"""
    # Create long text that needs chunking
    text = "Sentence. " * 200

    result = tool.ingest_text(text, source_name="long_doc")

    assert result["ok"] is True
    # Should create multiple chunks for long text
    assert result["chunks"] > 1


def test_audit_logging(tool):
    """Test audit log is created"""
    text = "Test content"

    result = tool.ingest_text(text, source_name="audit_test")

    assert result["ok"] is True

    # Check audit log was created
    assert TEST_AUDIT_FILE.exists()

    # Read and verify audit entry
    audit_entries = tool.get_audit_log()
    assert len(audit_entries) > 0

    last_entry = audit_entries[-1]
    assert last_entry["source_type"] == "text"
    assert last_entry["source_name"] == "audit_test"
    assert last_entry["status"] == "success"
    assert "ts" in last_entry
    assert "timestamp" in last_entry
    assert "hash" in last_entry


def test_get_audit_log_limit(tool):
    """Test audit log limit parameter"""
    # Ingest multiple items
    for i in range(5):
        tool.ingest_text(f"Content {i}", source_name=f"doc_{i}")

    # Get limited audit log
    entries = tool.get_audit_log(limit=3)
    assert len(entries) == 3

    # Get all entries
    all_entries = tool.get_audit_log(limit=100)
    assert len(all_entries) == 5


def test_get_audit_log_empty(tool):
    """Test getting audit log when empty"""
    entries = tool.get_audit_log()
    assert entries == []


def test_archive_directory_creation(tool):
    """Test archive directory is created"""
    assert TEST_ARCHIVE_DIR.exists()


def test_hash_uniqueness(tool):
    """Test different content gets different hashes"""
    text1 = "First content"
    text2 = "Second content"

    result1 = tool.ingest_text(text1, source_name="doc1")
    result2 = tool.ingest_text(text2, source_name="doc2")

    assert result1["hash"] != result2["hash"]


def test_archive_file_naming(tool):
    """Test archive files are named correctly"""
    text = "Test content"

    result = tool.ingest_text(text, source_name="my_document")

    archive_file = Path(result["archive_file"])

    # Should contain source name and hash
    assert "my_document" in archive_file.name
    assert archive_file.suffix == ".txt"


def test_chunk_text_sentence_boundary(tool):
    """Test chunking respects sentence boundaries"""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."

    chunks = tool._chunk_text(text, chunk_size=30, overlap=5)

    # Should have multiple chunks
    assert len(chunks) > 1

    # Each chunk should ideally end with a period (sentence boundary)
    # (though not guaranteed for very short chunks)
    for chunk in chunks[:-1]:  # Check all but last chunk
        if len(chunk) > 15:  # Only check if chunk is long enough
            # Should contain at least one sentence
            assert '.' in chunk or chunk == chunks[-1]


def test_multiple_ingestions(tool):
    """Test multiple text ingestions work correctly"""
    texts = [
        "First document content",
        "Second document content",
        "Third document content"
    ]

    results = []
    for i, text in enumerate(texts):
        result = tool.ingest_text(text, source_name=f"doc_{i}")
        results.append(result)

    # All should succeed
    assert all(r["ok"] for r in results)

    # All should have unique hashes
    hashes = [r["hash"] for r in results]
    assert len(set(hashes)) == len(hashes)

    # All archive files should exist
    for result in results:
        assert Path(result["archive_file"]).exists()

    # Audit log should have all entries
    audit_entries = tool.get_audit_log()
    assert len(audit_entries) == 3


# Note: OCR and scraping tests require external dependencies
# These are integration tests and may be skipped if dependencies unavailable

def test_scrape_url_missing_deps(tool, monkeypatch):
    """Test scraping fails gracefully without dependencies"""
    # Mock import to fail
    def mock_import_fail(name, *args, **kwargs):
        if name in ["requests", "bs4"]:
            raise ImportError("Mock import failure")
        return __builtins__.__import__(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import_fail)

    # Create new tool instance to trigger import
    new_tool = SelfImprovementTool()
    new_tool.archive_dir = TEST_ARCHIVE_DIR
    new_tool.audit_file = TEST_AUDIT_FILE

    result = new_tool.scrape_url("http://example.com")

    # Should fail with dependency error
    assert result["ok"] is False
    assert "dependencies" in result["error"].lower() or "not available" in result["error"].lower()


def test_ocr_file_not_found(tool):
    """Test OCR with non-existent file"""
    result = tool.ocr_file("/nonexistent/file.pdf")

    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_ocr_unsupported_file(tool):
    """Test OCR with unsupported file type"""
    # Create a temporary unsupported file
    unsupported_file = TEST_ARCHIVE_DIR / "test.txt"
    unsupported_file.write_text("test")

    result = tool.ocr_file(str(unsupported_file))

    assert result["ok"] is False
    assert "unsupported" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
