# nccgest - полная инструкция по API библиотеки (RU)

Документ описывает публичный Python API библиотеки `nccgest`, чтобы можно было передать его разработчикам приложения как готовую инструкцию по интеграции.

## Установка

```bash
pip install nccgest
```

Для разработки:

```bash
pip install -e ".[dev]"
```

## Основные классы

- `NCCGestClient` - синхронный клиент.
- `AsyncNCCGestClient` - асинхронный клиент.

Импорт:

```python
from nccgest import NCCGestClient, AsyncNCCGestClient
```

## Конструкторы клиентов

## `NCCGestClient(...)`

Параметры:

- `domain: str` - значение `dominio` для NCCGEST.
- `token: str` - API токен.
- `base_url: str = "https://api.nccgest.com/api/rest_api.php"` - endpoint API.
- `timeout: float = 30.0` - timeout HTTP клиента.
- `client: httpx.Client | None = None` - внешний клиент (опционально).

Поддерживает context manager:

```python
with NCCGestClient(domain="...", token="...") as api:
    ...
```

## `AsyncNCCGestClient(...)`

Параметры аналогичны sync-версии, но `client: httpx.AsyncClient | None`.

Поддерживает async context manager:

```python
async with AsyncNCCGestClient(domain="...", token="...") as api:
    ...
```

## Методы библиотеки

Ниже перечислены все публичные методы (sync и async имеют одинаковый контракт).

## 1) `read_services(start_date, end_date=None, *, subclass=None, paxname=None)`

Назначение: получить список услуг (`cmd_read`).

Вход:

- `start_date: str` - дата начала, формат `dd/mm/yyyy`.
- `end_date: str | None` - дата окончания, формат `dd/mm/yyyy` (опционально).
- `subclass: str | None` - фильтр по внешнему ID/коду.
- `paxname: str | None` - фильтр по имени пассажира.

Выход:

- `list[dict]` - список услуг (`payload["data"]`).
- По уточнению поддержки NCCGEST: поле `driver` в `cmd_read` всегда строка (или пустая строка), не объект.

Исключения:

- `NCCGestAPIError` - `success=false` со стороны API.
- `NCCGestHTTPError` - HTTP/транспортная ошибка.
- `NCCGestResponseError` - невалидный ответ/формат.

Пример:

```python
services = api.read_services("16/03/2026", "16/03/2026")
```

## 2) `insert_service(service)`

Назначение: создать услугу (`cmd_insert`).

Вход:

- `service: InsertServicePayload` (`dict`).

Минимально обязательные поля для корректного `cmd_insert`:

- `pickup`
- `dropoff`
- `date` (`dd/mm/yyyy`)
- `pickup_time` (`hh:mm`)
- `pax`
- `paxname`
- `paxphone`

Рекомендуемые поля:

- `subclass`
- `servicetype`
- `cartype`
- `price`
- `flight_train`, `flight_train_origin`
- `pickup_address`, `dropoff_address`
- `operator_note`

Выход:

- `int` - `serviceid` созданной записи.

Исключения:

- `NCCGestResponseError` если `serviceid` отсутствует/нечисловой.
- `NCCGestAPIError`, `NCCGestHTTPError`.

Пример:

```python
service_id = api.insert_service(
    {
        "pickup": "FCO",
        "dropoff": "Roma",
        "date": "16/03/2026",
        "pickup_time": "10:30",
        "pax": 2,
        "paxname": "John Smith",
        "paxphone": "+39000000000",
        "subclass": "EXT-ORDER-12345",
        "servicetype": "!!! --- TEST --- !!!",
        "cartype": "Business Class",
    }
)
```

## 3) `update_service(serviceid, service)`

Назначение: обновить услугу (`cmd_update`).

Вход:

- `serviceid: int` - ID услуги.
- `service: UpdateServicePayload` (`dict`) - поля для обновления.

Выход:

- `None` (если обновление успешно).

Исключения:

- `NCCGestAPIError`, `NCCGestHTTPError`, `NCCGestResponseError`.

Пример:

```python
api.update_service(
    serviceid=1234,
    service={
        "paxname": "Updated Name",
        "service_status": 2,
    },
)
```

## 4) `get_customer_data(vat)`

Назначение: получить клиентов по VAT (`cmd_customer`).

Вход:

- `vat: str`

Выход:

- `list[dict]` из `payload["data"]`.

Пример:

```python
customers = api.get_customer_data("IT12345678901")
```

## 5) `get_driver_data(driverid)`

Назначение: получить данные водителя (`cmd_driver`).

Вход:

- `driverid: int`

Выход:

- `list[dict]` из `payload["data"]`.

Пример:

```python
drivers = api.get_driver_data(101)
```

## Типы payload

Библиотека содержит типы:

- `InsertServicePayload`
- `UpdateServicePayload`

Они описаны в:

- `src/nccgest/types.py`

Их можно использовать для типизации своего кода.

## Исключения библиотеки

- `NCCGestError` - базовое.
- `NCCGestHTTPError` - HTTP/сетевые ошибки.
- `NCCGestResponseError` - невалидный JSON/неожиданный формат.
- `NCCGestAPIError` - API вернул `success=false`.

Пример обработки:

```python
from nccgest import NCCGestAPIError, NCCGestHTTPError, NCCGestResponseError

try:
    data = api.read_services("16/03/2026")
except NCCGestAPIError as e:
    print("API error:", e)
except NCCGestHTTPError as e:
    print("HTTP error:", e)
except NCCGestResponseError as e:
    print("Response error:", e)
```

## Асинхронный пример end-to-end

```python
import asyncio
from nccgest import AsyncNCCGestClient

async def main() -> None:
    async with AsyncNCCGestClient(domain="test", token="TEST_TOKEN") as api:
        services = await api.read_services("16/03/2026")
        print("services:", len(services))

        new_id = await api.insert_service(
            {
                "pickup": "FCO",
                "dropoff": "Roma",
                "date": "17/03/2026",
                "pickup_time": "10:30",
                "pax": 1,
                "paxname": "Async User",
                "paxphone": "+39000000000",
            }
        )
        print("new service id:", new_id)

        await api.update_service(new_id, {"service_status": 2})
        driver = await api.get_driver_data(101)
        print(driver)

asyncio.run(main())
```

## Мини-чеклист интеграции

- Создайте один экземпляр клиента на жизненный цикл операции/запроса.
- Передавайте даты в формате `dd/mm/yyyy`, время в `hh:mm`.
- На создание услуг не отправляйте параллельные вызовы без очереди.
- Всегда логируйте `NCCGestAPIError` и текст ошибки API.

## Mock-сервис: проверка зависимостей

При запуске `nccgest-mock` библиотека проверяет наличие модулей для mock-режима.
Если чего-то не хватает, команда завершится с подсказкой:

```bash
pip install "nccgest[mock]"
# или
pip install -e ".[mock]"
```
