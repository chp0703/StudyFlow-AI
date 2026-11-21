"""Exceptions for Daily Learning material indexing."""

from backend.app.ingestion.document import (
    IndexingError,
    IndexTimeoutError,
    IndexUnavailableError,
    InvalidDocumentError,
)

__all__ = [
    "IndexingError",
    "IndexTimeoutError",
    "InvalidDocumentError",
    "IndexUnavailableError",
]
