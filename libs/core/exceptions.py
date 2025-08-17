"""Base exceptions for the domain layer."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain level exceptions."""


class NotFoundError(DomainError):
    """Raised when an entity cannot be located."""


class ValidationError(DomainError):
    """Raised when data fails domain validation rules."""


# Alias to keep a generic name for error type hints
Error = DomainError

__all__ = ["DomainError", "NotFoundError", "ValidationError", "Error"]
