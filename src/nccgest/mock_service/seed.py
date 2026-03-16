"""Seed DB from YAML fixture file."""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List

import yaml

from . import storage


def seed_if_empty(conn: sqlite3.Connection, seed_file: str) -> None:
    if storage.count_services(conn) > 0:
        return
    if not os.path.exists(seed_file):
        storage.ensure_token(conn, "TEST_TOKEN", "test")
        return

    with open(seed_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return

    tokens = data.get("tokens", [])
    for item in tokens:
        if isinstance(item, dict):
            storage.ensure_token(
                conn,
                str(item.get("token", "TEST_TOKEN")),
                str(item.get("dominio", "test")),
            )

    services = _as_list(data.get("services"))
    customers = _as_list(data.get("customers"))
    drivers = _as_list(data.get("drivers"))

    storage.upsert_services(conn, services)
    storage.upsert_customers(conn, customers)
    storage.upsert_drivers(conn, drivers)


def _as_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
