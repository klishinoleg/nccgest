from __future__ import annotations

from typing import List

import httpx
import pytest

from nccgest import AsyncNCCGestClient, NCCGestAPIError, NCCGestClient, NCCGestError


def test_read_services_sync() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["cmd"] == "cmd_read"
        assert request.url.params["dominio"] == "mydomain"
        return httpx.Response(200, json={"success": True, "data": [{"id": "1"}], "error": ""})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, timeout=5.0) as http_client:
        client = NCCGestClient(domain="mydomain", token="token123", client=http_client)
        services = client.read_services("16/03/2026", "16/03/2026")
        assert services[0]["id"] == "1"


def test_insert_service_sync_returns_serviceid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["cmd"] == "cmd_insert"
        return httpx.Response(200, json={"success": True, "serviceid": 99, "error": ""})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, timeout=5.0) as http_client:
        client = NCCGestClient(domain="mydomain", token="token123", client=http_client)
        service_id = client.insert_service(
            {
                "pickup": "FCO",
                "dropoff": "Rome",
                "date": "16/03/2026",
                "pickup_time": "10:00",
                "pax": 1,
                "paxname": "Mario Rossi",
                "paxphone": "+39000000000",
            }
        )
        assert service_id == 99


def test_api_error_sync() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False, "error": "invalid token"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, timeout=5.0) as http_client:
        client = NCCGestClient(domain="mydomain", token="bad-token", client=http_client)
        with pytest.raises(NCCGestAPIError):
            client.read_services("16/03/2026")


@pytest.mark.asyncio
async def test_get_driver_async() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["cmd"] == "cmd_driver"
        return httpx.Response(
            200,
            json={"success": True, "data": [{"name": "Mario", "lastname": "Rossi"}], "error": ""},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, timeout=5.0) as http_client:
        client = AsyncNCCGestClient(domain="mydomain", token="token123", client=http_client)
        drivers = await client.get_driver_data(100)
        assert drivers[0]["name"] == "Mario"


def test_separate_tokens_sync() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url.params.get("token", "")))
        cmd = request.url.params["cmd"]
        if cmd == "cmd_read":
            return httpx.Response(200, json={"success": True, "data": [], "error": ""})
        if cmd == "cmd_driver":
            return httpx.Response(
                200,
                json={"success": True, "data": [{"name": "Mario"}], "error": ""},
            )
        return httpx.Response(400, json={"success": False, "error": "bad cmd"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, timeout=5.0) as http_client:
        client = NCCGestClient(
            domain="mydomain",
            customer_token="cust-token",
            master_token="master-token",
            client=http_client,
        )
        _ = client.read_services("16/03/2026")
        _ = client.get_driver_data(100)

    assert calls == ["cust-token", "master-token"]


def test_missing_master_token_raises() -> None:
    client = NCCGestClient(domain="mydomain", customer_token="cust-token")
    with pytest.raises(NCCGestError):
        _ = client.get_driver_data(1)
