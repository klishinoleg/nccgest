"""Mock NCCGEST service package."""

from .app import create_app
from .settings import MockSettings

__all__ = ["create_app", "MockSettings"]

