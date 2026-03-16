"""Settings for mock NCCGEST service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MockSettings:
    """Runtime settings for the mock service."""

    login: str = "test"
    password: str = "test"
    dbdir: str = "/data"
    port: int = 8255
    session_secret: str = "nccgest-mock-session-secret"
    seed_file: str = "tests/mock_data/services.yaml"

    @property
    def db_path(self) -> str:
        return os.path.join(self.dbdir, "nccgest_mock.sqlite3")

    @classmethod
    def from_env(cls) -> "MockSettings":
        port_raw = os.getenv("NCCGEST_PORT", "8255")
        try:
            port = int(port_raw)
        except ValueError:
            port = 8255

        return cls(
            login=os.getenv("NCCGEST_LOGIN", "test"),
            password=os.getenv("NCCGEST_PASSWORD", "test"),
            dbdir=os.getenv("NCCGEST_DBDIR", "/data"),
            port=port,
            session_secret=os.getenv("NCCGEST_SESSION_SECRET", "nccgest-mock-session-secret"),
            seed_file=os.getenv("NCCGEST_SEED_FILE", "tests/mock_data/services.yaml"),
        )

