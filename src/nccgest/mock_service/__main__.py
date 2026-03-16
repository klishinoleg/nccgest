"""Run mock NCCGEST FastAPI server."""

from __future__ import annotations

import uvicorn

from .app import create_app
from .settings import MockSettings


def main() -> None:
    settings = MockSettings.from_env()
    app = create_app(settings)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()

