from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMClient(ABC):
    """Abstract interface for language model interactions."""

    @abstractmethod
    def generate_structured_notes(self, text: str) -> List[Dict[str, Any]]:
        """Return list of structured insights extracted from raw text."""

    @abstractmethod
    def group_topics(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group insights into topics structure."""

    @abstractmethod
    def render_note_markdown(self, insight: Dict[str, Any]) -> str:
        """Render Markdown note for a given insight."""

    @abstractmethod
    def generate_moc(self, topics_json: str) -> str:
        """Generate Markdown MOC document from topics JSON."""

    @abstractmethod
    def find_autolinks(
        self, title: str, summary: str, candidates: List[str]
    ) -> List[str]:
        """Find related note titles from candidate list."""

    @abstractmethod
    def answer_from_context(self, query: str, fragments: List[Dict[str, str]]) -> str:
        """Answer a query using provided context fragments."""
