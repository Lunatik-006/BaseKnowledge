try:  # pragma: no cover - optional dependency
    from .vector_index import VectorIndex
except Exception:  # pragma: no cover - missing pymilvus
    class VectorIndex:  # type: ignore[misc]
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("pymilvus is required")
