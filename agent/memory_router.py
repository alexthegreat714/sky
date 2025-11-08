"""
Sky Memory Router
Handles short-term and long-term memory storage logic

Memory Architecture:
- Short-term: Rotating context window (last N entries)
- Long-term: Persistent, scored entries that survive pruning
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('SkyMemory')


class MemoryRouter:
    """
    Routes memory entries to short-term or long-term storage
    based on importance scoring and retention rules
    """

    def __init__(self, memory_dir='memory'):
        self.memory_dir = Path(memory_dir)
        self.short_term_path = self.memory_dir / 'short_term.jsonl'
        self.long_term_path = self.memory_dir / 'long_term.jsonl'

        # Ensure memory directory exists
        self.memory_dir.mkdir(exist_ok=True)

        # Configuration
        self.SHORT_TERM_LIMIT = 100  # Max entries before rotation
        self.LONG_TERM_THRESHOLD = 7  # Score threshold for long-term storage

    def write_short_term(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Write entry to short-term memory

        Args:
            content: The memory content
            metadata: Optional metadata (tags, context, etc.)

        Returns:
            The memory entry that was written
        """
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'content': content,
            'metadata': metadata or {},
            'score': 0  # Will be scored for long-term promotion
        }

        with open(self.short_term_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        logger.info(f"Short-term memory written: {content[:50]}...")
        return entry

    def write_long_term(self, content: str, score: int, metadata: Optional[Dict] = None) -> Dict:
        """
        Write entry to long-term memory (requires score)

        Args:
            content: The memory content
            score: Importance score (0-10)
            metadata: Optional metadata

        Returns:
            The memory entry that was written
        """
        if score < self.LONG_TERM_THRESHOLD:
            logger.warning(f"Score {score} below threshold {self.LONG_TERM_THRESHOLD}, not writing to long-term")
            return None

        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'content': content,
            'score': score,
            'metadata': metadata or {},
            'committed': True
        }

        with open(self.long_term_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        logger.info(f"Long-term memory committed (score={score}): {content[:50]}...")
        return entry

    def read_short_term(self, limit: Optional[int] = None) -> List[Dict]:
        """Read recent short-term memory entries"""
        if not self.short_term_path.exists():
            return []

        entries = []
        with open(self.short_term_path, 'r') as f:
            for line in f:
                entries.append(json.loads(line.strip()))

        # Return most recent entries
        if limit:
            return entries[-limit:]
        return entries

    def read_long_term(self, limit: Optional[int] = None) -> List[Dict]:
        """Read long-term memory entries"""
        if not self.long_term_path.exists():
            return []

        entries = []
        with open(self.long_term_path, 'r') as f:
            for line in f:
                entries.append(json.loads(line.strip()))

        if limit:
            return entries[-limit:]
        return entries

    def search_memory(self, query: str, search_long_term: bool = True) -> List[Dict]:
        """
        Search memory for entries matching query

        Args:
            query: Search term
            search_long_term: Whether to include long-term memory

        Returns:
            List of matching memory entries
        """
        results = []

        # Search short-term
        for entry in self.read_short_term():
            if query.lower() in entry['content'].lower():
                results.append(entry)

        # Search long-term if enabled
        if search_long_term:
            for entry in self.read_long_term():
                if query.lower() in entry['content'].lower():
                    results.append(entry)

        logger.info(f"Memory search for '{query}': {len(results)} results")
        return results

    def rotate_short_term(self):
        """
        Rotate short-term memory if limit exceeded
        Scores entries and promotes high-value ones to long-term
        """
        entries = self.read_short_term()

        if len(entries) <= self.SHORT_TERM_LIMIT:
            return

        # TODO: Implement scoring logic
        # For now, keep most recent entries
        logger.info(f"Rotating short-term memory ({len(entries)} -> {self.SHORT_TERM_LIMIT})")

        with open(self.short_term_path, 'w') as f:
            for entry in entries[-self.SHORT_TERM_LIMIT:]:
                f.write(json.dumps(entry) + '\n')


if __name__ == '__main__':
    # Test memory router
    router = MemoryRouter()
    router.write_short_term("Sky initialized successfully", {'type': 'system'})
    print(router.read_short_term())
