"""
Sky Memory Inspector - Browse, promote, and delete memories

Features:
- List short-term and long-term memories
- Promote memories to RAG vectorstore
- Delete specific memories
- Comprehensive audit logging
- FastAPI endpoints and CLI
"""
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal

# Setup logging
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)
LOG_FILE = LOG_DIR / "memory_audit.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
BASE = Path(__file__).resolve().parents[2]
MEM_DIR = BASE / "memory"
ST_FILE = MEM_DIR / "short_term.jsonl"
LT_FILE = MEM_DIR / "long_term.jsonl"
RAG_DIR = BASE / "sky" / "rag" / "chroma_store"

# Safe imports
def _safe_import(path, name):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

ingest_to_rag = _safe_import("src.rag.shared_ingest", "ingest_paths")


class MemoryInspector:
    """Manages memory inspection and manipulation"""

    def __init__(self):
        MEM_DIR.mkdir(parents=True, exist_ok=True)
        RAG_DIR.mkdir(parents=True, exist_ok=True)

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        """Read all entries from JSONL file with IDs"""
        if not path.exists():
            return []

        entries = []
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Add ID based on line number + content hash
                    content = entry.get("content", "")
                    entry_hash = hashlib.md5(f"{idx}:{content}".encode()).hexdigest()[:8]
                    entry["id"] = entry_hash
                    entry["line_number"] = idx
                    entries.append(entry)
                except Exception as e:
                    logger.error(f"Failed to parse line {idx}: {e}")
                    continue
        return entries

    def _write_jsonl(self, path: Path, entries: List[Dict[str, Any]]):
        """Write entries to JSONL file (without IDs)"""
        with path.open("w", encoding="utf-8") as f:
            for entry in entries:
                # Remove temporary fields
                clean_entry = {k: v for k, v in entry.items()
                              if k not in ["id", "line_number"]}
                f.write(json.dumps(clean_entry, ensure_ascii=False) + "\n")

    def _get_file_path(self, memory_type: Literal["short", "long"]) -> Path:
        """Get file path for memory type"""
        if memory_type == "short":
            return ST_FILE
        elif memory_type == "long":
            return LT_FILE
        else:
            raise ValueError(f"Invalid memory type: {memory_type}")

    def list_memories(self, memory_type: Literal["short", "long"] = "short") -> List[Dict[str, Any]]:
        """
        List all memories of specified type

        Args:
            memory_type: "short" or "long"

        Returns:
            List of memory entries with IDs
        """
        file_path = self._get_file_path(memory_type)
        entries = self._read_jsonl(file_path)

        logger.info(f"Listed {len(entries)} {memory_type}-term memories")
        return entries

    def get_memory(self, memory_id: str, memory_type: Literal["short", "long"] = "short") -> Optional[Dict[str, Any]]:
        """
        Get specific memory by ID

        Args:
            memory_id: Memory ID (hash)
            memory_type: "short" or "long"

        Returns:
            Memory entry or None if not found
        """
        entries = self.list_memories(memory_type)
        for entry in entries:
            if entry.get("id") == memory_id:
                return entry
        return None

    def promote_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Promote memory from short-term to long-term + RAG

        Args:
            memory_id: ID of memory to promote

        Returns:
            Result dict with status
        """
        # Find memory in short-term
        memory = self.get_memory(memory_id, memory_type="short")
        if not memory:
            logger.warning(f"Memory {memory_id} not found in short-term")
            return {"ok": False, "error": "Memory not found"}

        content = memory.get("content", "")
        if not content:
            logger.warning(f"Memory {memory_id} has no content")
            return {"ok": False, "error": "Memory has no content"}

        # Read all short-term memories
        st_entries = self._read_jsonl(ST_FILE)

        # Remove from short-term
        st_entries = [e for e in st_entries if e.get("id") != memory_id]

        # Prepare for long-term (mark as promoted)
        promoted_entry = {k: v for k, v in memory.items()
                         if k not in ["id", "line_number"]}
        promoted_entry["type"] = "long"
        promoted_entry["promoted_at"] = datetime.now().isoformat()
        promoted_entry["importance"] = max(memory.get("importance", 0.7), 0.7)

        # Write to long-term
        with LT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(promoted_entry, ensure_ascii=False) + "\n")

        # Update short-term (remove promoted entry)
        self._write_jsonl(ST_FILE, st_entries)

        # Ingest to RAG if available
        rag_success = False
        if callable(ingest_to_rag):
            try:
                ingest_to_rag([content])
                rag_success = True
                logger.info(f"Memory {memory_id} ingested to RAG")
            except Exception as e:
                logger.error(f"RAG ingest failed: {e}")

        # Audit log
        logger.info(f"Promoted memory {memory_id}: {content[:50]}...")

        return {
            "ok": True,
            "memory_id": memory_id,
            "content": content,
            "rag_ingested": rag_success,
            "promoted_at": promoted_entry["promoted_at"]
        }

    def delete_memory(self, memory_id: str, memory_type: Literal["short", "long"] = "short") -> Dict[str, Any]:
        """
        Delete memory permanently

        Args:
            memory_id: ID of memory to delete
            memory_type: "short" or "long"

        Returns:
            Result dict with status
        """
        file_path = self._get_file_path(memory_type)
        entries = self._read_jsonl(file_path)

        # Find and remove memory
        original_count = len(entries)
        deleted_memory = None

        filtered_entries = []
        for entry in entries:
            if entry.get("id") == memory_id:
                deleted_memory = entry
            else:
                filtered_entries.append(entry)

        if not deleted_memory:
            logger.warning(f"Memory {memory_id} not found in {memory_type}-term")
            return {"ok": False, "error": "Memory not found"}

        # Write updated list
        self._write_jsonl(file_path, filtered_entries)

        # Audit log
        logger.info(f"Deleted {memory_type}-term memory {memory_id}: {deleted_memory.get('content', '')[:50]}...")

        return {
            "ok": True,
            "memory_id": memory_id,
            "memory_type": memory_type,
            "content": deleted_memory.get("content", ""),
            "deleted_at": datetime.now().isoformat()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        st_count = len(self._read_jsonl(ST_FILE))
        lt_count = len(self._read_jsonl(LT_FILE))

        return {
            "short_term": {
                "count": st_count,
                "file": str(ST_FILE)
            },
            "long_term": {
                "count": lt_count,
                "file": str(LT_FILE)
            },
            "rag": {
                "enabled": callable(ingest_to_rag),
                "store": str(RAG_DIR)
            }
        }


# FastAPI integration
def create_memory_api():
    """Create FastAPI app for memory management"""
    try:
        from fastapi import FastAPI, HTTPException, Query
        from pydantic import BaseModel
    except ImportError:
        logger.error("FastAPI not available")
        return None

    app = FastAPI(title="Sky Memory Inspector API")
    inspector = MemoryInspector()

    @app.get("/memory/list")
    def list_memories(type: Literal["short", "long"] = Query("short")):
        """List memories of specified type"""
        memories = inspector.list_memories(memory_type=type)
        return {
            "type": type,
            "count": len(memories),
            "memories": memories
        }

    @app.get("/memory/stats")
    def get_stats():
        """Get memory statistics"""
        return inspector.get_stats()

    @app.get("/memory/get")
    def get_memory(id: str, type: Literal["short", "long"] = Query("short")):
        """Get specific memory by ID"""
        memory = inspector.get_memory(id, memory_type=type)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        return memory

    @app.post("/memory/promote")
    def promote_memory(id: str):
        """Promote memory to long-term + RAG"""
        result = inspector.promote_memory(id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @app.delete("/memory/delete")
    def delete_memory(id: str, type: Literal["short", "long"] = Query("short")):
        """Delete memory"""
        result = inspector.delete_memory(id, memory_type=type)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    return app


# CLI entry point
def main():
    """Main entry point for memory inspector"""
    import argparse

    parser = argparse.ArgumentParser(description="Sky Memory Inspector")
    parser.add_argument("--list", action="store_true", help="List memories")
    parser.add_argument("--type", choices=["short", "long"], default="short",
                       help="Memory type (default: short)")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--promote", type=str, help="Promote memory by ID")
    parser.add_argument("--delete", type=str, help="Delete memory by ID")
    parser.add_argument("--api-port", type=int, default=None,
                       help="Start API server on port")
    args = parser.parse_args()

    inspector = MemoryInspector()

    if args.api_port:
        # Start API server
        try:
            import uvicorn
            app = create_memory_api()
            if app:
                logger.info(f"Starting API server on port {args.api_port}")
                uvicorn.run(app, host="0.0.0.0", port=args.api_port)
            else:
                logger.error("Failed to create API app")
        except ImportError:
            logger.error("uvicorn not available - install with: pip install uvicorn")

    elif args.stats:
        # Show statistics
        stats = inspector.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.list:
        # List memories
        memories = inspector.list_memories(memory_type=args.type)
        print(f"\n{args.type.capitalize()}-term memories ({len(memories)}):\n")
        for mem in memories:
            print(f"  [{mem['id']}] {mem.get('content', '')[:80]}")
            print(f"    - importance: {mem.get('importance', 'N/A')}")
            print(f"    - tags: {mem.get('tags', [])}")
            print()

    elif args.promote:
        # Promote memory
        result = inspector.promote_memory(args.promote)
        if result.get("ok"):
            print(f"✓ Promoted memory {args.promote}")
            print(f"  Content: {result['content'][:80]}...")
            print(f"  RAG ingested: {result['rag_ingested']}")
        else:
            print(f"✗ Failed: {result.get('error')}")

    elif args.delete:
        # Delete memory
        result = inspector.delete_memory(args.delete, memory_type=args.type)
        if result.get("ok"):
            print(f"✓ Deleted {args.type}-term memory {args.delete}")
            print(f"  Content: {result['content'][:80]}...")
        else:
            print(f"✗ Failed: {result.get('error')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
