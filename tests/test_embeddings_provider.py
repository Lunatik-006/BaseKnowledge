from types import SimpleNamespace
import sys
from unittest.mock import patch

# Provide a stub for the "replicate" module used in EmbeddingsProvider
sys.modules.setdefault("replicate", SimpleNamespace(run=lambda *args, **kwargs: None))

from libs.llm.embeddings_provider import EmbeddingsProvider


def test_embed_texts_with_cache_and_batches():
    provider = EmbeddingsProvider(batch_size=2, embedding_dim=3)
    fake_output = {"embeddings": [[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]]}

    with patch("libs.llm.embeddings_provider.replicate.run", return_value=fake_output) as mock_run:
        texts = ["foo", "bar", "foo"]
        result = provider.embed_texts(texts)

    assert result == fake_output["embeddings"] + [fake_output["embeddings"][0]]
    assert mock_run.call_count == 1
