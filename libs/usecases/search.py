from __future__ import annotations

from typing import List, Dict

from libs.llm import LLMClient, EmbeddingsProvider
from libs.rag import VectorIndex
from libs.storage import NotesStorage


MAX_SNIPPET_LEN = 200


class Search:
    """Run semantic search over notes and compose an LLM answer."""

    def __init__(
        self,
        llm: LLMClient,
        embeddings: EmbeddingsProvider,
        index: VectorIndex,
        storage: NotesStorage,
    ) -> None:
        self.llm = llm
        self.embeddings = embeddings
        self.index = index
        self.storage = storage

    # ------------------------------------------------------------------
    def __call__(self, query: str, k: int = 5) -> tuple[str, List[Dict[str, str]]]:
        query_vec = self.embeddings.embed_texts([query])[0]
        hits = self.index.search(query_vec, k)
        fragments: List[Dict[str, str]] = []
        for hit in hits:
            try:
                note = self.storage.read_note(hit["note_id"])
            except FileNotFoundError:
                # Skip hits pointing to notes that no longer exist
                continue
            snippet = hit["text"]
            if len(snippet) > MAX_SNIPPET_LEN:
                snippet = snippet[: MAX_SNIPPET_LEN - 3].rstrip() + "..."
            fragments.append(
                {
                    "note_id": hit["note_id"],
                    "title": note.title,
                    "url": f"obsidian://{note.slug}",
                    "snippet": snippet,
                }
            )
        answer = self.llm.answer_from_context(query, fragments)
        return answer, fragments
