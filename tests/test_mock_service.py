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
            params={
                "dominio": "test",
                "token": "TEST_MASTER_TOKEN",
                "cmd": "cmd_driver",
                "driverid": 101,
            },
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
                "token": "TEST_MASTER_TOKEN",
                "cmd": "cmd_customer",
                "vat": "IT12345678901",
            },
        )
        assert api_response.status_code == 200
        assert api_response.json()["data"][0]["ragsoc"] == "NCCGEST UPDATED"


def test_mock_rest_api_commands(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app) as client:
        customer_params = {"dominio": "test", "token": "TEST_CUSTOMER_TOKEN"}
        master_params = {"dominio": "test", "token": "TEST_MASTER_TOKEN"}

        read_response = client.get(
            "/api/rest_api.php",
            params={**customer_params, "cmd": "cmd_read", "start_date": "16/03/2026"},
        )
        assert read_response.status_code == 200
        assert read_response.json()["success"] is True

        wrong_customer_token = client.get(
            "/api/rest_api.php",
            params={**master_params, "cmd": "cmd_read", "start_date": "16/03/2026"},
        )
        assert wrong_customer_token.status_code == 200
        assert wrong_customer_token.json()["success"] is False
        assert wrong_customer_token.json()["error"] == "Invalid Token"

        wrong_token_response = client.get(
            "/api/rest_api.php",
            params={**customer_params, "cmd": "cmd_customer", "vat": "IT12345678901"},
        )
        assert wrong_token_response.status_code == 200
        assert wrong_token_response.json()["success"] is False
        assert wrong_token_response.json()["error"] == "Invalid Token"

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
            params={**customer_params, "cmd": "cmd_insert"},
            json=insert_payload,
        )
        assert insert_response.status_code == 200
        serviceid = insert_response.json()["serviceid"]

        update_payload = {"serviceid": serviceid, "paxname": "Alice Updated", "service_status": 2}
        update_response = client.post(
            "/api/rest_api.php",
            params={**customer_params, "cmd": "cmd_update"},
            json=update_payload,
        )
        assert update_response.status_code == 200
        assert update_response.json()["success"] is True

        inserted_read = client.get(
            "/api/rest_api.php",
            params={
                **customer_params,
                "cmd": "cmd_read",
                "start_date": "17/03/2026",
                "end_date": "17/03/2026",
                "paxname": "Alice Updated",
            },
        )
        assert inserted_read.status_code == 200
        inserted_items = inserted_read.json()["data"]
        assert len(inserted_items) == 1
        assert int(inserted_items[0]["customer_id"]) == 1
        assert inserted_items[0]["customer"] == "NCCGEST SRLS"

        external_driver_insert = client.post(
            "/api/rest_api.php",
            params={**customer_params, "cmd": "cmd_insert"},
            json={
                "pickup": "CIA",
                "dropoff": "Roma",
                "date": "17/03/2026",
                "pickup_time": "12:00",
                "pax": 1,
                "paxname": "External Driver Pax",
                "paxphone": "+39000999888",
                "external_driver": "Partner Driver Name",
            },
        )
        assert external_driver_insert.status_code == 200
        assert external_driver_insert.json()["success"] is True

        external_driver_read = client.get(
            "/api/rest_api.php",
            params={
                **customer_params,
                "cmd": "cmd_read",
                "start_date": "17/03/2026",
                "end_date": "17/03/2026",
                "paxname": "External Driver Pax",
            },
        )
        assert external_driver_read.status_code == 200
        external_items = external_driver_read.json()["data"]
        assert len(external_items) == 1
        assert external_items[0]["driver"] == "Partner Driver Name"

        client.post("/admin/login", data={"username": "test", "password": "test"})
        service_admin = client.get(f"/admin/services/{serviceid}")
        assert service_admin.status_code == 200
        assert "service_status" in service_admin.text
        assert 'name="service_status"' in service_admin.text
        assert "2 - Confirmed" in service_admin.text
        assert 'name="incasso_serv"' in service_admin.text

        customer_response = client.get(
            "/api/rest_api.php",
            params={**master_params, "cmd": "cmd_customer", "vat": "IT12345678901"},
        )
        assert customer_response.status_code == 200
        assert customer_response.json()["data"][0]["ragsoc"] == "NCCGEST SRLS"

        driver_response = client.get(
            "/api/rest_api.php",
            params={**master_params, "cmd": "cmd_driver", "driverid": 101},
        )
        assert driver_response.status_code == 200
        assert driver_response.json()["data"][0]["name"] == "Mario"


def test_admin_crud_with_customer_driver_binding(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app) as client:
        customer_params = {"dominio": "test", "token": "TEST_CUSTOMER_TOKEN"}
        master_params = {"dominio": "test", "token": "TEST_MASTER_TOKEN"}
        client.post("/admin/login", data={"username": "test", "password": "test"})

        customer_create = client.post(
            "/admin/customers/new",
            data={
                "ragsoc": "ACME TEST TRAVEL",
                "address": "Via Roma 1",
                "city": "Roma",
                "province": "RM",
                "postalcode": "00100",
                "email": "acme@example.com",
                "piva": "ITTEST000001",
                "cf": "CFTEST000001",
            },
        )
        assert customer_create.status_code == 200

        customer_lookup = client.get(
            "/api/rest_api.php",
            params={**master_params, "cmd": "cmd_customer", "vat": "ITTEST000001"},
        )
        assert customer_lookup.status_code == 200
        customer_data = customer_lookup.json()["data"][0]
        customer_id = int(customer_data["id"])
        assert customer_data["ragsoc"] == "ACME TEST TRAVEL"

        generated = client.post(f"/admin/customers/{customer_id}/generate-token")
        assert generated.status_code == 200
        customer_edit_page = client.get(f"/admin/customers/{customer_id}")
        assert customer_edit_page.status_code == 200
        assert "Generate token" in customer_edit_page.text

        driver_create = client.post(
            "/admin/drivers/new",
            data={
                "id": "501",
                "name": "John",
                "lastname": "Doe",
                "phone_number": "+39111222333",
                "email": "john@example.com",
                "latitude": "41.9",
                "longitude": "12.5",
                "speed": "0",
                "datetime": "17/03/2026 10:00:00",
            },
        )
        assert driver_create.status_code == 200

        service_create = client.post(
            "/admin/services/new",
            data={
                "date": "17/03/2026",
                "time": "11:30",
                "pickup": "FCO",
                "pickup_address": "FCO",
                "dropoff": "Rome",
                "dropoff_address": "Via Test 1",
                "pax": "2",
                "paxname": "Binding Test Pax",
                "paxphone": "+39000111222",
                "subclass": "BINDING-001",
                "servicetype": "!!! --- TEST --- !!!",
                "cartype": "VAN (6 pax)",
                "service_status": "2",
                "customer_id": str(customer_id),
                "ids_ccp": str(customer_id),
                "ids_driver": "501",
                "internal_driverid": "501",
            },
        )
        assert service_create.status_code == 200

        read_response = client.get(
            "/api/rest_api.php",
            params={
                **customer_params,
                "cmd": "cmd_read",
                "start_date": "17/03/2026",
                "end_date": "17/03/2026",
                "paxname": "Binding Test Pax",
            },
        )
        assert read_response.status_code == 200
        services = read_response.json()["data"]
        assert len(services) == 1
        service = services[0]
        assert service["customer_id"] == customer_id
        assert service["customer"] == "ACME TEST TRAVEL"
        assert service["driver"] == "John Doe - +39111222333"

        service_id = int(service["id"])
        service_delete = client.post(f"/admin/services/{service_id}/delete")
        assert service_delete.status_code == 200

        driver_delete = client.post("/admin/drivers/501/delete")
        assert driver_delete.status_code == 200
        driver_read = client.get(
            "/api/rest_api.php",
            params={**master_params, "cmd": "cmd_driver", "driverid": "501"},
        )
        assert driver_read.status_code == 200
        assert driver_read.json()["data"] == []

        customer_delete = client.post(f"/admin/customers/{customer_id}/delete")
        assert customer_delete.status_code == 200
        customer_read = client.get(
            "/api/rest_api.php",
            params={**master_params, "cmd": "cmd_customer", "vat": "ITTEST000001"},
        )
        assert customer_read.status_code == 200
        assert customer_read.json()["data"] == []


def test_sync_client_with_mock_service(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    with TestClient(app, base_url="http://testserver") as http_client:
        with NCCGestClient(
            domain="test",
            customer_token="TEST_CUSTOMER_TOKEN",
            master_token="TEST_MASTER_TOKEN",
            base_url="http://testserver/api/rest_api.php",
            client=http_client,
        ) as api:
            services = api.read_services("16/03/2026")
            assert len(services) >= 1
            drivers = api.get_driver_data(101)
            assert drivers[0]["name"] == "Mario"


@pytest.mark.asyncio
async def test_async_client_with_mock_service(tmp_path: Path) -> None:
    app = create_app(_make_settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        async with AsyncNCCGestClient(
            domain="test",
            customer_token="TEST_CUSTOMER_TOKEN",
            master_token="TEST_MASTER_TOKEN",
            base_url="http://testserver/api/rest_api.php",
            client=http_client,
        ) as api:
            data = await api.get_driver_data(101)
            assert data[0]["name"] == "Mario"
