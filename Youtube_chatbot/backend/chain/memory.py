"""
Conversation memory: session-keyed sliding window of last k turns.
"""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Turn:
    human: str
    ai: str


class SessionMemory:
    """
    In-memory conversation store, keyed by session_id.
    Keeps the last `k` turns per session.
    """

    def __init__(self, k: int = 5):
        self.k = k
        self._store: dict[str, list[Turn]] = defaultdict(list)

    def add_turn(self, session_id: str, human: str, ai: str):
        self._store[session_id].append(Turn(human=human, ai=ai))
        # Slide window
        if len(self._store[session_id]) > self.k:
            self._store[session_id] = self._store[session_id][-self.k:]

    def get_history(self, session_id: str) -> str:
        """Return formatted chat history string."""
        turns = self._store[session_id]
        if not turns:
            return "(no previous conversation)"
        lines = []
        for t in turns:
            lines.append(f"Human: {t.human}")
            lines.append(f"Assistant: {t.ai}")
        return "\n".join(lines)

    def clear(self, session_id: str):
        self._store.pop(session_id, None)


# Singleton shared across the app
memory = SessionMemory(k=5)
