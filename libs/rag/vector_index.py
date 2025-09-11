from typing import List, Dict, Any

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)

from libs.core.settings import get_settings


class VectorIndex:
    """Wrapper around Milvus vector store."""

    def __init__(
        self,
        uri: str | None = None,
        dim: int | None = None,
        create_notes_meta: bool = False,
    ) -> None:
        # Resolve configuration from settings if not explicitly provided
        settings = get_settings()
        self.dim = dim if dim is not None else getattr(settings, "embedding_dim", 768)
        if uri:
            self.uri = uri
        else:
            self.uri = settings.milvus_uri
        if not self.uri:
            raise RuntimeError("MILVUS_URI is not set")
        # pymilvus requires a URI with an explicit scheme. Users may provide
        # just "host:port" in the environment which results in a connection
        # error.  To be more forgiving, automatically prepend "http://" when
        # no scheme is supplied so that both "http://milvus:19530" and
        # "milvus:19530" work the same.
        if not self.uri.startswith("http://") and not self.uri.startswith("https://"):
            self.uri = f"http://{self.uri}"

        connections.connect("default", uri=self.uri)

        self.chunks_collection = "chunks"
        self.notes_meta_collection = "notes_meta"

        self._ensure_chunks_collection()
        if create_notes_meta:
            self._ensure_notes_meta_collection()

    # Internal helpers -------------------------------------------------
    def _ensure_chunks_collection(self) -> None:
        if utility.has_collection(self.chunks_collection):
            # Validate schema: ensure primary key is VARCHAR and embedding dim matches
            try:
                existing = Collection(self.chunks_collection)
                fields = {f.name: f for f in existing.schema.fields}
                cid = fields.get("chunk_id")
                emb = fields.get("embedding")
                cid_ok = getattr(cid, "dtype", None) == DataType.VARCHAR
                # dim may be exposed differently depending on pymilvus version
                emb_dim = getattr(emb, "dim", None)
                if emb_dim is None:
                    params = getattr(emb, "params", None) or getattr(emb, "type_params", {})
                    emb_dim = int(params.get("dim")) if isinstance(params, dict) and params.get("dim") else None
                dim_ok = emb_dim == self.dim if emb_dim is not None else True
                if cid_ok and dim_ok:
                    return
                # Drop incompatible collection and recreate
                existing.release()
                utility.drop_collection(self.chunks_collection)
            except Exception:
                # If we cannot introspect the schema (e.g., in tests with stubs),
                # assume it's compatible and skip recreation.
                return

        # Use string IDs to match our DB schema (UUID strings)
        fields = [
            FieldSchema(
                name="chunk_id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            ),
            FieldSchema(name="note_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="pos", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
        ]
        schema = CollectionSchema(fields, description="note chunks")
        collection = Collection(self.chunks_collection, schema=schema)

        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        collection.load()

    def _ensure_notes_meta_collection(self) -> None:
        if utility.has_collection(self.notes_meta_collection):
            return
        fields = [
            FieldSchema(name="note_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
        ]
        schema = CollectionSchema(fields, description="notes metadata")
        Collection(self.notes_meta_collection, schema=schema)

    # Public API -------------------------------------------------------
    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Insert or update chunk records."""
        collection = Collection(self.chunks_collection)
        data = [
            [c["chunk_id"] for c in chunks],
            [c["note_id"] for c in chunks],
            [c["pos"] for c in chunks],
            [c["text"] for c in chunks],
            [c["embedding"] for c in chunks],
        ]
        collection.upsert(data)

    def search(self, query_vec: List[float], k: int = 5) -> List[Dict[str, Any]]:
        collection = Collection(self.chunks_collection)
        collection.load()
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        results = collection.search(
            data=[query_vec],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["chunk_id", "note_id", "pos", "text"],
        )
        hits: List[Dict[str, Any]] = []
        for hit in results[0]:
            entity = hit.entity
            hits.append(
                {
                    "chunk_id": entity.get("chunk_id"),
                    "note_id": entity.get("note_id"),
                    "pos": entity.get("pos"),
                    "text": entity.get("text"),
                    "score": hit.score,
                }
            )
        return hits
