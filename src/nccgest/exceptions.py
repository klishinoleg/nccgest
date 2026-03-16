"""Custom exceptions for NCCGEST client."""

from __future__ import annotations

from typing import Optional


class NCCGestError(Exception):
    """Base package exception."""


class NCCGestHTTPError(NCCGestError):
    """Transport-level HTTP error."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NCCGestResponseError(NCCGestError):
    """Invalid/unexpected response payload."""


class NCCGestAPIError(NCCGestError):
    """API-level error returned by NCCGEST."""

    def __init__(self, message: str, response: Optional[dict] = None) -> None:
        super().__init__(message)
        self.response = response or {}

