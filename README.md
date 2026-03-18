# nccgest

[English](README.md) | [Italiano](README.it.md) | [Русский](README.ru.md)

Python package for synchronous and asynchronous interaction with the NCCGEST REST API.

Full method-by-method documentation:

- [docs/library_api.ru.md](C:/python/pip/nccgest/docs/library_api.ru.md) (RU)

## Features

- Sync client: `NCCGestClient`
- Async client: `AsyncNCCGestClient`
- Command coverage:
  - `cmd_read`
  - `cmd_insert`
  - `cmd_update`
  - `cmd_customer`
  - `cmd_driver`
- Typed API errors and HTTP errors
- Python `3.8+` support (recommended runtime: `3.10+`)

## Installation

```bash
pip install nccgest
```

## Quick Start (sync)

```python
from nccgest import NCCGestClient

with NCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
    services = client.read_services(start_date="16/03/2026", end_date="16/03/2026")
    print(services)
```

## Token Types

According to NCCGEST support:

- `cmd_read`, `cmd_insert`, `cmd_update` use **Customer Token**
- `cmd_customer`, `cmd_driver` use **Master Token**

You can pass them separately:

```python
from nccgest import NCCGestClient

client = NCCGestClient(
    domain="your-domain",
    customer_token="CUSTOMER_TOKEN",
    master_token="MASTER_TOKEN",
)
```

Backward compatibility: `token=...` still works and is used for both token types.

## `cmd_read` Status Values

`status` in `cmd_read` response is a string with one of:

- `Canceled`
- `Waiting`
- `Confirmed`

In library typing this field is strict: `ServiceStatus = Literal["Canceled", "Waiting", "Confirmed"]`.

## Quick Start (async)

```python
import asyncio
from nccgest import AsyncNCCGestClient

async def main() -> None:
    async with AsyncNCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
        driver_data = await client.get_driver_data(driverid=123)
        print(driver_data)

asyncio.run(main())
```

## Insert Service Example

```python
from nccgest import NCCGestClient

payload = {
    "pickup": "FCO",
    "dropoff": "Roma",
    "date": "16/03/2026",
    "pickup_time": "10:30",
    "pax": 2,
    "paxname": "John Smith",
    "paxphone": "+39000000000",
    "servicetype": "Transfer",
    "cartype": "Business Class",
    "subclass": "EXT-ORDER-12345",
}

with NCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
    service_id = client.insert_service(payload)
    print(service_id)
```

## API Notes

- Use HTTPS only.
- NCCGEST API docs mention no concurrent inserts: avoid parallel create calls.
- Use proper URL encoding for external inputs.
- Follow official endpoint method mapping (`GET` for read/customer/driver, `POST` for insert/update).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Mock Service (FastAPI + SQLite)

Install mock dependencies:

```bash
pip install -e ".[mock]"
```

Run:

```bash
NCCGEST_LOGIN=test NCCGEST_PASSWORD=test NCCGEST_DBDIR=/data NCCGEST_PORT=8255 python -m nccgest.mock_service
```

Alternative command:

```bash
nccgest-mock
```

If required mock modules are missing, `nccgest-mock` prints install instructions:

```bash
pip install "nccgest[mock]"
# or for local repo:
pip install -e ".[mock]"
```

Web UI:

- Login page: `http://localhost:8255/admin/login`
- Services admin: `http://localhost:8255/admin/services`
- Customers admin: `http://localhost:8255/admin/customers`
- Drivers admin: `http://localhost:8255/admin/drivers`
- API endpoint: `http://localhost:8255/api/rest_api.php`

The `/data` directory is ignored by git and used for the local SQLite DB.
Mock YAML fixtures for tests are stored in `tests/mock_data/services.yaml`.
UI templates and CSS are separated in:

- `src/nccgest/mock_service/templates/*.html`
- `src/nccgest/mock_service/static/style.css`
