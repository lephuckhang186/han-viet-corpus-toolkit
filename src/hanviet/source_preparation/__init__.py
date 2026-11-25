"""Source preparation: PDF/TXT region cropping, workspace management, and undo history."""

from .models import Book, Box, Source, validate_assignment, validate_work
from .workspace import Workspace

__all__ = [
    "Book",
    "Box",
    "Source",
    "Workspace",
    "validate_assignment",
    "validate_work",
]
