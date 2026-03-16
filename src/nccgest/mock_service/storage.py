"""SQLite storage layer for mock service."""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, Iterable, List, Optional


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS api_tokens (
            token TEXT PRIMARY KEY,
            dominio TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            pickup TEXT NOT NULL,
            pickup_address TEXT NOT NULL DEFAULT '',
            dropoff TEXT NOT NULL,
            dropoff_address TEXT NOT NULL DEFAULT '',
            transport_number TEXT NOT NULL DEFAULT '',
            transport_from TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Confirmed',
            pax INTEGER NOT NULL DEFAULT 1,
            paxname TEXT NOT NULL DEFAULT '',
            paxphone TEXT NOT NULL DEFAULT '',
            subclass TEXT NOT NULL DEFAULT '',
            servicetype TEXT NOT NULL DEFAULT 'Transfer',
            cartype TEXT NOT NULL DEFAULT '',
            vehicle_plate TEXT NOT NULL DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            vat REAL NOT NULL DEFAULT 10,
            operator_note TEXT NOT NULL DEFAULT '',
            service_status INTEGER NOT NULL DEFAULT 2
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ragsoc TEXT NOT NULL,
            address TEXT NOT NULL DEFAULT '-',
            city TEXT NOT NULL DEFAULT '-',
            province TEXT NOT NULL DEFAULT '-',
            postalcode TEXT NOT NULL DEFAULT '-',
            email TEXT NOT NULL DEFAULT '',
            piva TEXT NOT NULL DEFAULT '',
            cf TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            lastname TEXT NOT NULL,
            phone_number TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            latitude TEXT NOT NULL DEFAULT '',
            longitude TEXT NOT NULL DEFAULT '',
            speed TEXT NOT NULL DEFAULT '',
            datetime TEXT NOT NULL DEFAULT ''
        );
        """
    )
    conn.commit()


def token_exists(conn: sqlite3.Connection, token: str, dominio: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM api_tokens WHERE token = ? AND dominio = ? LIMIT 1",
        (token, dominio),
    ).fetchone()
    return row is not None


def ensure_token(conn: sqlite3.Connection, token: str, dominio: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO api_tokens(token, dominio) VALUES (?, ?)",
        (token, dominio),
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


def get_service(conn: sqlite3.Connection, serviceid: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM services WHERE id = ?", (serviceid,)).fetchone()
    if row is None:
        return None
    return dict(row)


def insert_service(conn: sqlite3.Connection, payload: Dict[str, Any]) -> int:
    values = {
        "date": payload.get("date", ""),
        "time": payload.get("pickup_time", ""),
        "pickup": payload.get("pickup", ""),
        "pickup_address": payload.get("pickup_address", ""),
        "dropoff": payload.get("dropoff", ""),
        "dropoff_address": payload.get("dropoff_address", ""),
        "transport_number": payload.get("flight_train", ""),
        "transport_from": payload.get("flight_train_origin", ""),
        "status": "Confirmed",
        "pax": _as_int(payload.get("pax"), 0),
        "paxname": payload.get("paxname", ""),
        "paxphone": payload.get("paxphone", ""),
        "subclass": payload.get("subclass", ""),
        "servicetype": payload.get("servicetype", ""),
        "cartype": payload.get("cartype", ""),
        "vehicle_plate": payload.get("vehicle_plate", ""),
        "price": float(payload.get("price", 0) or 0),
        "vat": float(payload.get("vat", 10) or 10),
        "operator_note": payload.get("operator_note", ""),
        "service_status": _as_int(payload.get("service_status"), 2),
    }
    cur = conn.execute(
        """
        INSERT INTO services(
            date, time, pickup, pickup_address, dropoff, dropoff_address,
            transport_number, transport_from, status, pax, paxname, paxphone,
            subclass, servicetype, cartype, vehicle_plate, price, vat,
            operator_note, service_status
        ) VALUES (
            :date, :time, :pickup, :pickup_address, :dropoff, :dropoff_address,
            :transport_number, :transport_from, :status, :pax, :paxname, :paxphone,
            :subclass, :servicetype, :cartype, :vehicle_plate, :price, :vat,
            :operator_note, :service_status
        )
        """,
        values,
    )
    conn.commit()
    if cur.lastrowid is None:
        raise RuntimeError("Unable to get inserted service ID.")
    return int(cur.lastrowid)


def update_service(conn: sqlite3.Connection, serviceid: int, payload: Dict[str, Any]) -> bool:
    service = get_service(conn, serviceid)
    if service is None:
        return False

    merged = dict(service)
    field_map = {
        "date": "date",
        "pickup_time": "time",
        "pickup": "pickup",
        "pickup_address": "pickup_address",
        "dropoff": "dropoff",
        "dropoff_address": "dropoff_address",
        "flight_train": "transport_number",
        "flight_train_origin": "transport_from",
        "pax": "pax",
        "paxname": "paxname",
        "paxphone": "paxphone",
        "subclass": "subclass",
        "servicetype": "servicetype",
        "cartype": "cartype",
        "vehicle_plate": "vehicle_plate",
        "price": "price",
        "vat": "vat",
        "operator_note": "operator_note",
        "service_status": "service_status",
    }
    for in_key, db_key in field_map.items():
        if in_key in payload and payload[in_key] is not None:
            merged[db_key] = payload[in_key]

    status_map = {0: "Canceled", 1: "Waiting", 2: "Confirmed"}
    status_value = _as_int(merged.get("service_status"), 2)
    merged["status"] = status_map.get(status_value, "Confirmed")

    conn.execute(
        """
        UPDATE services SET
            date = :date,
            time = :time,
            pickup = :pickup,
            pickup_address = :pickup_address,
            dropoff = :dropoff,
            dropoff_address = :dropoff_address,
            transport_number = :transport_number,
            transport_from = :transport_from,
            status = :status,
            pax = :pax,
            paxname = :paxname,
            paxphone = :paxphone,
            subclass = :subclass,
            servicetype = :servicetype,
            cartype = :cartype,
            vehicle_plate = :vehicle_plate,
            price = :price,
            vat = :vat,
            operator_note = :operator_note,
            service_status = :service_status
        WHERE id = :id
        """,
        {
            "id": serviceid,
            "date": merged["date"],
            "time": merged["time"],
            "pickup": merged["pickup"],
            "pickup_address": merged["pickup_address"],
            "dropoff": merged["dropoff"],
            "dropoff_address": merged["dropoff_address"],
            "transport_number": merged["transport_number"],
            "transport_from": merged["transport_from"],
            "status": merged["status"],
            "pax": _as_int(merged["pax"], 0),
            "paxname": merged["paxname"],
            "paxphone": merged["paxphone"],
            "subclass": merged["subclass"],
            "servicetype": merged["servicetype"],
            "cartype": merged["cartype"],
            "vehicle_plate": merged["vehicle_plate"],
            "price": float(merged["price"]),
            "vat": float(merged["vat"]),
            "operator_note": merged["operator_note"],
            "service_status": _as_int(merged["service_status"], 2),
        },
    )
    conn.commit()
    return True


def list_customers_by_vat(conn: sqlite3.Connection, vat: str) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM customers WHERE piva = ?", (vat,)).fetchall()
    return [dict(row) for row in rows]


def get_driver_by_id(conn: sqlite3.Connection, driverid: int) -> List[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driverid,)).fetchone()
    if row is None:
        return []
    data = dict(row)
    data.pop("id", None)
    return [data]


def upsert_customers(conn: sqlite3.Connection, customers: Iterable[Dict[str, Any]]) -> None:
    for customer in customers:
        conn.execute(
            """
            INSERT INTO customers(ragsoc, address, city, province, postalcode, email, piva, cf)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer.get("ragsoc", ""),
                customer.get("address", "-"),
                customer.get("city", "-"),
                customer.get("province", "-"),
                customer.get("postalcode", "-"),
                customer.get("email", ""),
                customer.get("piva", ""),
                customer.get("cf", ""),
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
                driver.get("name", ""),
                driver.get("lastname", ""),
                driver.get("phone_number", ""),
                driver.get("email", ""),
                driver.get("latitude", ""),
                driver.get("longitude", ""),
                driver.get("speed", ""),
                driver.get("datetime", ""),
            ),
        )
    conn.commit()


def upsert_services(conn: sqlite3.Connection, services: Iterable[Dict[str, Any]]) -> None:
    for service in services:
        conn.execute(
            """
            INSERT OR REPLACE INTO services(
                id, date, time, pickup, pickup_address, dropoff, dropoff_address,
                transport_number, transport_from, status, pax, paxname, paxphone,
                subclass, servicetype, cartype, vehicle_plate, price, vat, operator_note,
                service_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _as_int(service.get("id"), 0),
                service.get("date", ""),
                service.get("time", ""),
                service.get("pickup", ""),
                service.get("pickup_address", ""),
                service.get("dropoff", ""),
                service.get("dropoff_address", ""),
                service.get("transport_number", ""),
                service.get("transport_from", ""),
                service.get("status", "Confirmed"),
                _as_int(service.get("pax"), 1),
                service.get("paxname", ""),
                service.get("paxphone", ""),
                service.get("subclass", ""),
                service.get("servicetype", "Transfer"),
                service.get("cartype", ""),
                service.get("vehicle_plate", ""),
                float(service.get("price", 0)),
                float(service.get("vat", 10)),
                service.get("operator_note", ""),
                _as_int(service.get("service_status"), 2),
            ),
        )
    conn.commit()


def count_services(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS cnt FROM services").fetchone()
    return int(row["cnt"]) if row is not None else 0


def _as_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def service_row_to_api(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "date": row["date"],
        "time": row["time"],
        "pickup_address": row["pickup_address"],
        "dropoff_address": row["dropoff_address"],
        "transport_number": row["transport_number"],
        "transport_from": row["transport_from"],
        "status": row["status"],
        "status_events": [],
        "pax": str(row["pax"]),
        "paxname": row["paxname"],
        "pax_list": [{"name": row["paxname"], "phone": row["paxphone"]}] if row["paxname"] else [],
        "subclass": row["subclass"],
        "servicetype": row["servicetype"],
        "cartype": row["cartype"],
        "vehicle_plate": row["vehicle_plate"],
        "driver": "",
        "external_driver": "",
        "ids_supplier": "",
        "customer_id": "",
        "customer": "",
        "price": row["price"],
        "vat": row["vat"],
    }
