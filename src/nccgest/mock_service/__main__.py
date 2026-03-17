"""Run mock NCCGEST FastAPI server."""

from __future__ import annotations

import importlib.util
import sys
from typing import List

from .settings import MockSettings

REQUIRED_MODULES = [
    "fastapi",
    "uvicorn",
    "jinja2",
    "itsdangerous",
    "yaml",
    "multipart",
]


def _missing_modules() -> List[str]:
    missing: List[str] = []
    for module_name in REQUIRED_MODULES:
        if importlib.util.find_spec(module_name) is None:
            missing.append(module_name)
    return missing


def main() -> None:
    missing = _missing_modules()
    if missing:
        mods = ", ".join(missing)
        print("Missing dependencies for `nccgest-mock`: " + mods, file=sys.stderr)
        print("Install with one of the commands:", file=sys.stderr)
        print("  pip install \"nccgest[mock]\"", file=sys.stderr)
        print("  pip install -e \".[mock]\"", file=sys.stderr)
        raise SystemExit(1)

    import uvicorn

    from .app import create_app

    settings = MockSettings.from_env()
    app = create_app(settings)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
