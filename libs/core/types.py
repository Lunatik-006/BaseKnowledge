"""Commonly used typing helpers."""

from __future__ import annotations

from typing import TypeAlias, TypeVar, Union

from .exceptions import Error

T = TypeVar("T")

# Result type: either a value of type ``T`` or an ``Error`` instance.
Result: TypeAlias = Union[T, Error]

__all__ = ["Result", "Error"]
