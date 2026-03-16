# nccgest

[English](README.md) | [Italiano](README.it.md) | [Русский](README.ru.md)

Python-библиотека для синхронной и асинхронной интеграции с REST API NCCGEST.

Полная инструкция по API библиотеки:

- [docs/library_api.ru.md](C:/python/pip/nccgest/docs/library_api.ru.md)

## Возможности

- Синхронный клиент: `NCCGestClient`
- Асинхронный клиент: `AsyncNCCGestClient`
- Поддерживаемые команды:
  - `cmd_read`
  - `cmd_insert`
  - `cmd_update`
  - `cmd_customer`
  - `cmd_driver`
- Типизированные ошибки API и HTTP
- Поддержка Python `3.8+` (рекомендуемый runtime: `3.10+`)

## Установка

```bash
pip install nccgest
```

## Быстрый старт (sync)

```python
from nccgest import NCCGestClient

with NCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
    services = client.read_services(start_date="16/03/2026", end_date="16/03/2026")
    print(services)
```

## Быстрый старт (async)

```python
import asyncio
from nccgest import AsyncNCCGestClient

async def main() -> None:
    async with AsyncNCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
        driver_data = await client.get_driver_data(driverid=123)
        print(driver_data)

asyncio.run(main())
```

## Примечания по API

- Использовать только HTTPS.
- Не отправлять вставки услуг параллельно.
- Выполнять URL encoding входных параметров.
- Соблюдать методы endpoint-ов из документации (`GET` для read/customer/driver, `POST` для insert/update).

## Mock-сервис (FastAPI + SQLite)

Установка зависимостей:

```bash
pip install -e ".[mock]"
```

Запуск:

```bash
NCCGEST_LOGIN=test NCCGEST_PASSWORD=test NCCGEST_DBDIR=/data NCCGEST_PORT=8255 python -m nccgest.mock_service
```

Или командой:

```bash
nccgest-mock
```

- Web UI (логин/списки/редактирование): `http://localhost:8255/admin/login`
- Услуги (админка): `http://localhost:8255/admin/services`
- Водители (админка): `http://localhost:8255/admin/drivers`
- API endpoint: `http://localhost:8255/api/rest_api.php`

Каталог `/data` исключен из git и используется для локальной SQLite базы.
Mock-фикстуры для автотестов лежат в `tests/mock_data/services.yaml`.
Шаблоны и стили вынесены отдельно:

- `src/nccgest/mock_service/templates/*.html`
- `src/nccgest/mock_service/static/style.css`
