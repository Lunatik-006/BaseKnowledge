"""Core library exposing domain models, settings, exceptions and types."""

from .config import Settings
from .exceptions import DomainError, NotFoundError, ValidationError, Error
from .models import User, Note, Chunk, SearchResult
from .types import Result

__all__ = [
    "Settings",
    "DomainError",
    "NotFoundError",
    "ValidationError",
    "Error",
    "User",
    "Note",
    "Chunk",
    "SearchResult",
    "Result",
]
