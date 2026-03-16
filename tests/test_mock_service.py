from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from nccgest import AsyncNCCGestClient, NCCGestClient
from nccgest.mock_service import MockSettings, create_app


def _make_settings(tmp_path: Path) -> MockSettings:
    seed_file = Path(__file__).parent / "mock_data" / "services.yaml"
    return MockSettings(
        login="test",
        password="test",
        dbdir=str(tmp_path),
        port=8255,
        seed_file=str(seed_file),
    )


def test_admin_login_and_list(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app) as client:
        response = client.get("/admin/login")
        assert response.status_code == 200
        login = client.post("/admin/login", data={"username": "test", "password": "test"})
        assert login.status_code == 200
        services = client.get("/admin/services")
        assert services.status_code == 200
        assert "Services" in services.text


def test_mock_rest_api_commands(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app) as client:
        base_params = {"dominio": "test", "token": "TEST_TOKEN"}

        read_response = client.get(
            "/api/rest_api.php",
            params={**base_params, "cmd": "cmd_read", "start_date": "16/03/2026"},
        )
        assert read_response.status_code == 200
        assert read_response.json()["success"] is True

        insert_payload = {
            "pickup": "FCO",
            "dropoff": "Roma",
            "date": "17/03/2026",
            "pickup_time": "10:30",
            "pax": 2,
            "paxname": "Alice Doe",
            "paxphone": "+39000123456",
            "subclass": "EXT-2",
            "servicetype": "!!! --- TEST --- !!!",
            "cartype": "Business Class",
        }
        insert_response = client.post(
            "/api/rest_api.php",
            params={**base_params, "cmd": "cmd_insert"},
            json=insert_payload,
        )
        assert insert_response.status_code == 200
        serviceid = insert_response.json()["serviceid"]

        update_payload = {"serviceid": serviceid, "paxname": "Alice Updated", "service_status": 2}
        update_response = client.post(
            "/api/rest_api.php",
            params={**base_params, "cmd": "cmd_update"},
            json=update_payload,
        )
        assert update_response.status_code == 200
        assert update_response.json()["success"] is True

        customer_response = client.get(
            "/api/rest_api.php",
            params={**base_params, "cmd": "cmd_customer", "vat": "IT12345678901"},
        )
        assert customer_response.status_code == 200
        assert customer_response.json()["data"][0]["ragsoc"] == "NCCGEST SRLS"

        driver_response = client.get(
            "/api/rest_api.php",
            params={**base_params, "cmd": "cmd_driver", "driverid": 101},
        )
        assert driver_response.status_code == 200
        assert driver_response.json()["data"][0]["name"] == "Mario"


def test_sync_client_with_mock_service(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app, base_url="http://testserver") as http_client:
        with NCCGestClient(
            domain="test",
            token="TEST_TOKEN",
            base_url="http://testserver/api/rest_api.php",
            client=http_client,
        ) as api:
            services = api.read_services("16/03/2026")
            assert len(services) >= 1


@pytest.mark.asyncio
async def test_async_client_with_mock_service(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        async with AsyncNCCGestClient(
            domain="test",
            token="TEST_TOKEN",
            base_url="http://testserver/api/rest_api.php",
            client=http_client,
        ) as api:
            data = await api.get_driver_data(101)
            assert data[0]["name"] == "Mario"
