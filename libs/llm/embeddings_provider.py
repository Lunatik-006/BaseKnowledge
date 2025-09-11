from __future__ import annotations

from typing import Dict, List

import replicate
from libs.core.settings import get_settings


class EmbeddingsProvider:
    """Simple interface to fetch embeddings from Replicate models."""

    def __init__(
        self,
        model: str | None = None,
        *,
        embedding_dim: int | None = None,
        batch_size: int = 32,
        enable_cache: bool = True,
    ) -> None:
        settings = get_settings()
        # Allow overriding via args; otherwise pull from settings with sane defaults
        self.model = model or getattr(
            settings, "embeddings_model", "nomic-ai/nomic-embed-text-v1.5"
        )
        self.embedding_dim = (
            embedding_dim if embedding_dim is not None else getattr(settings, "embedding_dim", 768)
        )
        self.batch_size = batch_size
        self.enable_cache = enable_cache
        self._cache: Dict[str, List[float]] = {}

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        output = replicate.run(self.model, input={"texts": texts})
        if isinstance(output, dict) and "embeddings" in output:
            embeddings = output["embeddings"]
        else:
            embeddings = output
        for emb in embeddings:
            if len(emb) != self.embedding_dim:
                raise ValueError(
                    f"Embedding size {len(emb)} does not match expected {self.embedding_dim}"
                )
        return embeddings

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float] | None] = [None] * len(texts)
        text_to_indices: Dict[str, List[int]] = {}

        for idx, text in enumerate(texts):
            if self.enable_cache and text in self._cache:
                results[idx] = self._cache[text]
            else:
                text_to_indices.setdefault(text, []).append(idx)

        uncached = [t for t in text_to_indices.keys() if not (self.enable_cache and t in self._cache)]

        for i in range(0, len(uncached), self.batch_size):
            batch = uncached[i : i + self.batch_size]
            embeddings = self._embed_batch(batch)
            for text, emb in zip(batch, embeddings):
                for idx in text_to_indices[text]:
                    results[idx] = emb
                if self.enable_cache:
                    self._cache[text] = emb

        return [emb for emb in results if emb is not None]
