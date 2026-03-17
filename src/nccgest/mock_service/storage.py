"""SQLite storage layer for mock service."""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, Iterable, List, Optional

SERVICE_COLUMNS: Dict[str, str] = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "date": "TEXT NOT NULL DEFAULT ''",
    "time": "TEXT NOT NULL DEFAULT ''",
    "pickup": "TEXT NOT NULL DEFAULT ''",
    "pickup_address": "TEXT NOT NULL DEFAULT ''",
    "dropoff": "TEXT NOT NULL DEFAULT ''",
    "dropoff_address": "TEXT NOT NULL DEFAULT ''",
    "dropoff_date": "TEXT NOT NULL DEFAULT ''",
    "dropoff_time": "TEXT NOT NULL DEFAULT ''",
    "transport_number": "TEXT NOT NULL DEFAULT ''",
    "transport_from": "TEXT NOT NULL DEFAULT ''",
    "status": "TEXT NOT NULL DEFAULT 'Confirmed'",
    "pax": "INTEGER NOT NULL DEFAULT 1",
    "bags": "INTEGER NOT NULL DEFAULT 0",
    "smallbags": "INTEGER NOT NULL DEFAULT 0",
    "pets": "INTEGER NOT NULL DEFAULT 0",
    "child_seat_1": "INTEGER NOT NULL DEFAULT 0",
    "child_seat_2": "INTEGER NOT NULL DEFAULT 0",
    "child_seat_3": "INTEGER NOT NULL DEFAULT 0",
    "paxname": "TEXT NOT NULL DEFAULT ''",
    "paxphone": "TEXT NOT NULL DEFAULT ''",
    "paxmail": "TEXT NOT NULL DEFAULT ''",
    "subclass": "TEXT NOT NULL DEFAULT ''",
    "servicetype": "TEXT NOT NULL DEFAULT 'Transfer'",
    "cartype": "TEXT NOT NULL DEFAULT ''",
    "vehicle_plate": "TEXT NOT NULL DEFAULT ''",
    "price": "REAL NOT NULL DEFAULT 0",
    "vat": "REAL NOT NULL DEFAULT 10",
    "service_note": "TEXT NOT NULL DEFAULT ''",
    "operator_note": "TEXT NOT NULL DEFAULT ''",
    "service_status": "INTEGER NOT NULL DEFAULT 2",
    "cash": "INTEGER NOT NULL DEFAULT 0",
    "comm_cliente": "REAL NOT NULL DEFAULT 0",
    "impincassato": "REAL NOT NULL DEFAULT 0",
    "servincassato": "REAL NOT NULL DEFAULT 0",
    "incasso_serv": "REAL NOT NULL DEFAULT 0",
    "invoice_receipt": "INTEGER NOT NULL DEFAULT 0",
    "number_invoice_receipt": "TEXT NOT NULL DEFAULT ''",
    "ids_supplier": "INTEGER NOT NULL DEFAULT 0",
    "ids_driver": "INTEGER NOT NULL DEFAULT 0",
    "ids_agente": "INTEGER NOT NULL DEFAULT 0",
    "ids_ccp": "INTEGER NOT NULL DEFAULT 0",
    "internal_driverid": "INTEGER NOT NULL DEFAULT 0",
    "external_driver": "TEXT NOT NULL DEFAULT ''",
    "comm_driver": "REAL NOT NULL DEFAULT 0",
    "comm_agent": "REAL NOT NULL DEFAULT 0",
}

NUMERIC_INT_FIELDS = {
    "pax",
    "bags",
    "smallbags",
    "pets",
    "child_seat_1",
    "child_seat_2",
    "child_seat_3",
    "service_status",
    "cash",
    "invoice_receipt",
    "ids_supplier",
    "ids_driver",
    "ids_agente",
    "ids_ccp",
    "internal_driverid",
}
NUMERIC_FLOAT_FIELDS = {
    "price",
    "vat",
    "comm_cliente",
    "impincassato",
    "servincassato",
    "incasso_serv",
    "comm_driver",
    "comm_agent",
}

CUSTOMER_COLUMNS: Dict[str, str] = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "ragsoc": "TEXT NOT NULL DEFAULT ''",
    "address": "TEXT NOT NULL DEFAULT '-'",
    "city": "TEXT NOT NULL DEFAULT '-'",
    "province": "TEXT NOT NULL DEFAULT '-'",
    "postalcode": "TEXT NOT NULL DEFAULT '-'",
    "email": "TEXT NOT NULL DEFAULT ''",
    "piva": "TEXT NOT NULL DEFAULT ''",
    "cf": "TEXT NOT NULL DEFAULT ''",
}

DRIVER_COLUMNS: Dict[str, str] = {
    "id": "INTEGER PRIMARY KEY",
    "name": "TEXT NOT NULL DEFAULT ''",
    "lastname": "TEXT NOT NULL DEFAULT ''",
    "phone_number": "TEXT NOT NULL DEFAULT ''",
    "email": "TEXT NOT NULL DEFAULT ''",
    "latitude": "TEXT NOT NULL DEFAULT ''",
    "longitude": "TEXT NOT NULL DEFAULT ''",
    "speed": "TEXT NOT NULL DEFAULT ''",
    "datetime": "TEXT NOT NULL DEFAULT ''",
}
API_TOKEN_COLUMNS: Dict[str, str] = {
    "token": "TEXT PRIMARY KEY",
    "dominio": "TEXT NOT NULL",
    "token_type": "TEXT NOT NULL DEFAULT 'both'",
}


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    _create_table_if_not_exists(conn, "api_tokens", API_TOKEN_COLUMNS)
    _ensure_columns(conn, "api_tokens", API_TOKEN_COLUMNS)
    _create_table_if_not_exists(conn, "services", SERVICE_COLUMNS)
    _create_table_if_not_exists(conn, "customers", CUSTOMER_COLUMNS)
    _create_table_if_not_exists(conn, "drivers", DRIVER_COLUMNS)
    _ensure_columns(conn, "services", SERVICE_COLUMNS)
    _ensure_columns(conn, "customers", CUSTOMER_COLUMNS)
    _ensure_columns(conn, "drivers", DRIVER_COLUMNS)
    conn.commit()


def token_exists(
    conn: sqlite3.Connection,
    token: str,
    dominio: str,
    required_token_type: Optional[str] = None,
) -> bool:
    row = conn.execute(
        "SELECT token_type FROM api_tokens WHERE token = ? AND dominio = ? LIMIT 1",
        (token, dominio),
    ).fetchone()
    if row is None:
        return False
    token_type = str(row["token_type"])
    if required_token_type is None:
        return True
    if token_type == "both":
        return True
    return token_type == required_token_type


def ensure_token(
    conn: sqlite3.Connection,
    token: str,
    dominio: str,
    token_type: str = "both",
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO api_tokens(token, dominio, token_type) VALUES (?, ?, ?)",
        (token, dominio, token_type),
    )
    conn.commit()


def list_services(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: Optional[str],
    subclass: Optional[str],
    paxname: Optional[str],
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM services WHERE date >= ?"
    args: List[Any] = [start_date]

    if end_date:
        query += " AND date <= ?"
        args.append(end_date)
    if subclass:
        query += " AND subclass = ?"
        args.append(subclass)
    if paxname:
        query += " AND paxname LIKE ?"
        args.append("%" + paxname + "%")
    query += " ORDER BY date, time, id"

    rows = conn.execute(query, args).fetchall()
    return [service_row_to_api(dict(row)) for row in rows]


def list_services_admin(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM services ORDER BY date, time, id").fetchall()
    return [dict(row) for row in rows]


def get_service(conn: sqlite3.Connection, serviceid: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM services WHERE id = ?", (serviceid,)).fetchone()
    if row is None:
        return None
    return dict(row)


def insert_service(conn: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    values = _normalize_service_payload(payload)
    columns = [col for col in values.keys() if col != "id"]
    placeholders = ", ".join(":" + col for col in columns)
    sql = "INSERT INTO services(" + ", ".join(columns) + ") VALUES (" + placeholders + ")"
    cur = conn.execute(sql, values)
    conn.commit()
    if cur.lastrowid is None:
        raise RuntimeError("Unable to get inserted service ID.")
    return int(cur.lastrowid)


def update_service(conn: sqlite3.Connection, serviceid: int, payload: Dict[str, Any]) -> bool:
    current = get_service(conn, serviceid)
    if current is None:
        return False

    merged = dict(current)
    normalized = _normalize_service_payload(payload)
    for key, value in normalized.items():
        if key in SERVICE_COLUMNS and key != "id":
            merged[key] = value

    status_map = {0: "Canceled", 1: "Waiting", 2: "Confirmed"}
    merged["status"] = status_map.get(_as_int(merged.get("service_status"), 2), "Confirmed")

    fields = [k for k in SERVICE_COLUMNS.keys() if k != "id"]
    assignments = ", ".join(k + " = :" + k for k in fields)
    merged["id"] = serviceid
    conn.execute("UPDATE services SET " + assignments + " WHERE id = :id", merged)
    conn.commit()
    return True


def list_customers_by_vat(conn: sqlite3.Connection, vat: str) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM customers WHERE piva = ?", (vat,)).fetchall()
    return [dict(row) for row in rows]


def list_customers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM customers ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_customer(conn: sqlite3.Connection, customerid: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customerid,)).fetchone()
    if row is None:
        return None
    return dict(row)


def update_customer(conn: sqlite3.Connection, customerid: int, payload: Dict[str, Any]) -> bool:
    current = get_customer(conn, customerid)
    if current is None:
        return False
    merged = dict(current)
    for key in CUSTOMER_COLUMNS.keys():
        if key == "id":
            continue
        if key in payload and payload[key] is not None:
            merged[key] = str(payload[key])

    merged["id"] = customerid
    fields = [k for k in CUSTOMER_COLUMNS.keys() if k != "id"]
    assignments = ", ".join(k + " = :" + k for k in fields)
    conn.execute("UPDATE customers SET " + assignments + " WHERE id = :id", merged)
    conn.commit()
    return True


def get_driver_by_id(conn: sqlite3.Connection, driverid: int) -> List[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driverid,)).fetchone()
    if row is None:
        return []
    data = dict(row)
    data.pop("id", None)
    return [data]


def list_drivers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM drivers ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_driver(conn: sqlite3.Connection, driverid: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driverid,)).fetchone()
    if row is None:
        return None
    return dict(row)


def update_driver(conn: sqlite3.Connection, driverid: int, payload: Dict[str, Any]) -> bool:
    current = get_driver(conn, driverid)
    if current is None:
        return False
    merged = dict(current)
    for key in DRIVER_COLUMNS.keys():
        if key == "id":
            continue
        if key in payload and payload[key] is not None:
            merged[key] = str(payload[key])
    merged["id"] = driverid
    fields = [k for k in DRIVER_COLUMNS.keys() if k != "id"]
    assignments = ", ".join(k + " = :" + k for k in fields)
    conn.execute("UPDATE drivers SET " + assignments + " WHERE id = :id", merged)
    conn.commit()
    return True


def upsert_customers(conn: sqlite3.Connection, customers: Iterable[Dict[str, Any]]) -> None:
    for customer in customers:
        data = {k: customer.get(k, "") for k in CUSTOMER_COLUMNS.keys()}
        if data.get("id"):
            conn.execute(
                """
                INSERT OR REPLACE INTO customers(
                    id, ragsoc, address, city, province, postalcode, email, piva, cf
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _as_int(data["id"], 0),
                    str(data["ragsoc"]),
                    str(data["address"] or "-"),
                    str(data["city"] or "-"),
                    str(data["province"] or "-"),
                    str(data["postalcode"] or "-"),
                    str(data["email"]),
                    str(data["piva"]),
                    str(data["cf"]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO customers(ragsoc, address, city, province, postalcode, email, piva, cf)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(data["ragsoc"]),
                    str(data["address"] or "-"),
                    str(data["city"] or "-"),
                    str(data["province"] or "-"),
                    str(data["postalcode"] or "-"),
                    str(data["email"]),
                    str(data["piva"]),
                    str(data["cf"]),
                ),
            )
    conn.commit()


def upsert_drivers(conn: sqlite3.Connection, drivers: Iterable[Dict[str, Any]]) -> None:
    for driver in drivers:
        conn.execute(
            """
            INSERT OR REPLACE INTO drivers(
                id, name, lastname, phone_number, email, latitude, longitude, speed, datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _as_int(driver.get("id"), 0),
                str(driver.get("name", "")),
                str(driver.get("lastname", "")),
                str(driver.get("phone_number", "")),
                str(driver.get("email", "")),
                str(driver.get("latitude", "")),
                str(driver.get("longitude", "")),
                str(driver.get("speed", "")),
                str(driver.get("datetime", "")),
            ),
        )
    conn.commit()


def upsert_services(conn: sqlite3.Connection, services: Iterable[Dict[str, Any]]) -> None:
    for service in services:
        normalized = _normalize_service_payload(service)
        if "id" in service and service["id"] is not None:
            normalized["id"] = _as_int(service["id"], 0)
            fields = [k for k in SERVICE_COLUMNS.keys()]
            placeholders = ", ".join(":" + k for k in fields)
            sql = (
                "INSERT OR REPLACE INTO services("
                + ", ".join(fields)
                + ") VALUES ("
                + placeholders
                + ")"
            )
            conn.execute(sql, {k: normalized.get(k, _service_default_value(k)) for k in fields})
        else:
            columns = [k for k in SERVICE_COLUMNS.keys() if k != "id"]
            placeholders = ", ".join(":" + k for k in columns)
            sql = "INSERT INTO services(" + ", ".join(columns) + ") VALUES (" + placeholders + ")"
            conn.execute(sql, {k: normalized.get(k, _service_default_value(k)) for k in columns})
    conn.commit()


def count_services(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS cnt FROM services").fetchone()
    return int(row["cnt"]) if row is not None else 0


def service_row_to_api(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "date": row["date"],
        "time": row["time"],
        "pickup_address": row["pickup_address"],
        "dropoff_address": row["dropoff_address"],
        "extra_stop": [],
        "transport_number": row["transport_number"],
        "transport_from": row["transport_from"],
        "status": row["status"],
        "status_events": "",
        "pax": row["pax"],
        "paxname": row["paxname"],
        "pax_list": [{"name": row["paxname"], "phone": row["paxphone"]}] if row["paxname"] else [],
        "subclass": row["subclass"],
        "servicetype": row["servicetype"],
        "cartype": row["cartype"],
        "vehicle_plate": row["vehicle_plate"],
        "driver": "",
        "external_driver": row.get("external_driver", ""),
        "ids_supplier": row.get("ids_supplier", ""),
        "customer_id": row.get("ids_ccp", ""),
        "customer": "",
        "price": row["price"],
        "vat": row["vat"],
        "service_note": row.get("service_note", ""),
    }


def _normalize_service_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    mapped: Dict[str, Any] = {}
    alias_map = {
        "pickup_time": "time",
        "flight_train": "transport_number",
        "flight_train_origin": "transport_from",
    }
    for key, value in payload.items():
        target_key = alias_map.get(key, key)
        if target_key in SERVICE_COLUMNS and target_key != "id":
            mapped[target_key] = value

    normalized = {k: _service_default_value(k) for k in SERVICE_COLUMNS.keys() if k != "id"}
    normalized.update(mapped)

    for key in NUMERIC_INT_FIELDS:
        normalized[key] = _as_int(normalized.get(key), _as_int(_service_default_value(key), 0))
    for key in NUMERIC_FLOAT_FIELDS:
        normalized[key] = _as_float(
            normalized.get(key),
            _as_float(_service_default_value(key), 0.0),
        )

    status_map = {0: "Canceled", 1: "Waiting", 2: "Confirmed"}
    normalized["status"] = status_map.get(_as_int(normalized.get("service_status"), 2), "Confirmed")
    for key in normalized.keys():
        if key not in NUMERIC_INT_FIELDS and key not in NUMERIC_FLOAT_FIELDS:
            normalized[key] = str(normalized[key])
    return normalized


def _service_default_value(key: str) -> Any:
    defaults: Dict[str, Any] = {
        "status": "Confirmed",
        "pax": 1,
        "bags": 0,
        "smallbags": 0,
        "pets": 0,
        "child_seat_1": 0,
        "child_seat_2": 0,
        "child_seat_3": 0,
        "price": 0.0,
        "vat": 10.0,
        "service_status": 2,
        "cash": 0,
        "comm_cliente": 0.0,
        "impincassato": 0.0,
        "servincassato": 0.0,
        "incasso_serv": 0.0,
        "invoice_receipt": 0,
        "ids_supplier": 0,
        "ids_driver": 0,
        "ids_agente": 0,
        "ids_ccp": 0,
        "internal_driverid": 0,
    }
    return defaults.get(key, "")


def _create_table_if_not_exists(
    conn: sqlite3.Connection,
    table_name: str,
    columns: Dict[str, str],
) -> None:
    sql = "CREATE TABLE IF NOT EXISTS " + table_name + " (" + ", ".join(
        col + " " + spec for col, spec in columns.items()
    ) + ")"
    conn.execute(sql)


def _ensure_columns(conn: sqlite3.Connection, table_name: str, columns: Dict[str, str]) -> None:
    existing_rows = conn.execute("PRAGMA table_info(" + table_name + ")").fetchall()
    existing = {row["name"] for row in existing_rows}
    for col, spec in columns.items():
        if col not in existing:
            if "PRIMARY KEY" in spec:
                continue
            conn.execute("ALTER TABLE " + table_name + " ADD COLUMN " + col + " " + spec)
    if table_name == "api_tokens":
        rows = conn.execute("SELECT token, dominio, token_type FROM api_tokens").fetchall()
        for row in rows:
            token_type = str(row["token_type"])
            if token_type not in {"customer", "master", "both"}:
                conn.execute(
                    "UPDATE api_tokens SET token_type = 'both' WHERE token = ? AND dominio = ?",
                    (row["token"], row["dominio"]),
                )


def _as_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
