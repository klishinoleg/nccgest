# nccgest

[English](README.md) | [Italiano](README.it.md) | [Русский](README.ru.md)

Python package for synchronous and asynchronous interaction with the NCCGEST REST API.

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

