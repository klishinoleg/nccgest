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
        assert "customers" in services.text.lower()


def test_admin_drivers_list_and_edit(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app) as client:
        client.post("/admin/login", data={"username": "test", "password": "test"})

        drivers = client.get("/admin/drivers")
        assert drivers.status_code == 200
        assert "Mario Rossi" in drivers.text

        edit_page = client.get("/admin/drivers/101")
        assert edit_page.status_code == 200
        assert "Edit driver #101" in edit_page.text

        update_response = client.post(
            "/admin/drivers/101",
            data={
                "name": "Mario",
                "lastname": "Rossi",
                "phone_number": "+39123456789",
                "email": "mario.updated@example.com",
                "latitude": "41.900",
                "longitude": "12.500",
                "speed": "0",
                "datetime": "16/03/2026 18:00:00",
            },
        )
        assert update_response.status_code == 200

        api_response = client.get(
            "/api/rest_api.php",
            params={"dominio": "test", "token": "TEST_TOKEN", "cmd": "cmd_driver", "driverid": 101},
        )
        assert api_response.status_code == 200
        assert api_response.json()["data"][0]["phone_number"] == "+39123456789"


def test_admin_customers_list_and_edit(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app) as client:
        client.post("/admin/login", data={"username": "test", "password": "test"})

        customers = client.get("/admin/customers")
        assert customers.status_code == 200
        assert "NCCGEST SRLS" in customers.text

        edit_page = client.get("/admin/customers/1")
        assert edit_page.status_code == 200
        assert "Edit customer #1" in edit_page.text

        update_response = client.post(
            "/admin/customers/1",
            data={
                "ragsoc": "NCCGEST UPDATED",
                "address": "Via New 10",
                "city": "Roma",
                "province": "RM",
                "postalcode": "00100",
                "email": "updated@example.com",
                "piva": "IT12345678901",
                "cf": "CF123456",
            },
        )
        assert update_response.status_code == 200

        api_response = client.get(
            "/api/rest_api.php",
            params={
                "dominio": "test",
                "token": "TEST_TOKEN",
                "cmd": "cmd_customer",
                "vat": "IT12345678901",
            },
        )
        assert api_response.status_code == 200
        assert api_response.json()["data"][0]["ragsoc"] == "NCCGEST UPDATED"


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

        client.post("/admin/login", data={"username": "test", "password": "test"})
        service_admin = client.get(f"/admin/services/{serviceid}")
        assert service_admin.status_code == 200
        assert "service_status" in service_admin.text

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
