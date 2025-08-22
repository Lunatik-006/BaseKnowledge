"""Core library exposing domain models, settings, exceptions and types."""

from .settings import Settings, get_settings
from .exceptions import DomainError, NotFoundError, ValidationError, Error
from .models import User, Note, Chunk, SearchResult
from .types import Result

__all__ = [
    "Settings",
    "get_settings",
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

