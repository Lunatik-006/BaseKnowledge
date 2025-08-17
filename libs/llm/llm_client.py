from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMClient(ABC):
    """Abstract interface for language model interactions."""

    @abstractmethod
    def generate_structured_notes(self, text: str) -> Dict[str, Any]:
        """Return structured insights extracted from raw text."""

    @abstractmethod
    def render_note_markdown(self, insight: Dict[str, Any]) -> str:
        """Render Markdown note for a given insight."""

    @abstractmethod
    def answer_from_context(self, query: str, fragments: List[Dict[str, str]]) -> str:
        """Answer a query using provided context fragments."""
