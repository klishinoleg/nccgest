# nccgest

[English](README.md) | [Italiano](README.it.md) | [Русский](README.ru.md)

Pacchetto Python per integrare in modo sincrono e asincrono la REST API di NCCGEST.

## Funzionalita

- Client sincrono: `NCCGestClient`
- Client asincrono: `AsyncNCCGestClient`
- Comandi supportati:
  - `cmd_read`
  - `cmd_insert`
  - `cmd_update`
  - `cmd_customer`
  - `cmd_driver`
- Errori API e HTTP tipizzati
- Supporto Python `3.8+` (runtime consigliato: `3.10+`)

## Installazione

```bash
pip install nccgest
```

## Esempio rapido (sync)

```python
from nccgest import NCCGestClient

with NCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
    services = client.read_services(start_date="16/03/2026", end_date="16/03/2026")
    print(services)
```

## Tipi di token

Secondo il supporto NCCGEST:

- `cmd_read`, `cmd_insert`, `cmd_update` richiedono **Customer Token**
- `cmd_customer`, `cmd_driver` richiedono **Master Token**

Nel client puoi passarli separatamente:

```python
from nccgest import NCCGestClient

client = NCCGestClient(
    domain="your-domain",
    customer_token="CUSTOMER_TOKEN",
    master_token="MASTER_TOKEN",
)
```

Compatibilita retroattiva: `token=...` viene usato per entrambi i tipi.

## Esempio rapido (async)

```python
import asyncio
from nccgest import AsyncNCCGestClient

async def main() -> None:
    async with AsyncNCCGestClient(domain="your-domain", token="YOUR_TOKEN") as client:
        driver_data = await client.get_driver_data(driverid=123)
        print(driver_data)

asyncio.run(main())
```

## Note API

- Usare solo HTTPS.
- Evitare inserimenti concorrenti in parallelo.
- Codificare correttamente i parametri (URL encoding).
- Rispettare i metodi endpoint della documentazione (`GET` per read/customer/driver, `POST` per insert/update).

## Servizio Mock (FastAPI + SQLite)

Installazione dipendenze:

```bash
pip install -e ".[mock]"
```

Avvio:

```bash
NCCGEST_LOGIN=test NCCGEST_PASSWORD=test NCCGEST_DBDIR=/data NCCGEST_PORT=8255 python -m nccgest.mock_service
```

Comando alternativo:

```bash
nccgest-mock
```

Se mancano moduli richiesti per il mock, `nccgest-mock` mostra i comandi di installazione:

```bash
pip install "nccgest[mock]"
# oppure per repository locale:
pip install -e ".[mock]"
```

- Web UI (login/lista/modifica): `http://localhost:8255/admin/login`
- Servizi admin: `http://localhost:8255/admin/services`
- Clienti admin: `http://localhost:8255/admin/customers`
- Driver admin: `http://localhost:8255/admin/drivers`
- API endpoint: `http://localhost:8255/api/rest_api.php`

La cartella `/data` e ignorata da git e contiene il DB SQLite locale.
I fixture YAML per i test sono in `tests/mock_data/services.yaml`.
Template e CSS separati:

- `src/nccgest/mock_service/templates/*.html`
- `src/nccgest/mock_service/static/style.css`
