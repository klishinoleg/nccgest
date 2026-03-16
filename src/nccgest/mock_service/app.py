"""FastAPI app implementing a mock NCCGEST service."""

from __future__ import annotations

import sqlite3
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware

from .seed import seed_if_empty
from .settings import MockSettings
from .storage import (
    connect,
    get_driver_by_id,
    get_service,
    init_schema,
    insert_service,
    list_customers_by_vat,
    list_services,
    token_exists,
    update_service,
)


def create_app(settings: Optional[MockSettings] = None) -> FastAPI:
    cfg = settings or MockSettings.from_env()
    app = FastAPI(title="NCCGEST Mock Service")
    app.add_middleware(SessionMiddleware, secret_key=cfg.session_secret)
    app.state.settings = cfg
    app.state.db = connect(cfg.db_path)
    _init_db(app.state.db, cfg)
    _register_routes(app)
    return app


def _init_db(conn: sqlite3.Connection, settings: MockSettings) -> None:
    init_schema(conn)
    seed_if_empty(conn, settings.seed_file)


def _register_routes(app: FastAPI) -> None:
    def login_required(handler: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(handler)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request = kwargs["request"]
            if not request.session.get("logged_in"):
                return RedirectResponse(url="/admin/login", status_code=303)
            return await handler(*args, **kwargs)

        return wrapper

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request) -> Response:
        if request.session.get("logged_in"):
            return RedirectResponse(url="/admin/services", status_code=303)
        return RedirectResponse(url="/admin/login", status_code=303)

    @app.get("/admin/login", response_class=HTMLResponse)
    async def admin_login_page(request: Request) -> HTMLResponse:
        return HTMLResponse(_render_login_page())

    @app.post("/admin/login", response_class=HTMLResponse)
    async def admin_login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
    ) -> Response:
        settings: MockSettings = request.app.state.settings
        if username == settings.login and password == settings.password:
            request.session["logged_in"] = True
            return RedirectResponse(url="/admin/services", status_code=303)
        return HTMLResponse(_render_login_page(error="Invalid credentials"), status_code=401)

    @app.post("/admin/logout")
    async def admin_logout(request: Request) -> RedirectResponse:
        request.session.clear()
        return RedirectResponse(url="/admin/login", status_code=303)

    @app.get("/admin/services", response_class=HTMLResponse)
    @login_required
    async def admin_services(request: Request) -> HTMLResponse:
        db = request.app.state.db
        items = list_services(db, "00/00/0000", None, None, None)
        return HTMLResponse(_render_services_page(items))

    @app.get("/admin/services/{serviceid}", response_class=HTMLResponse)
    @login_required
    async def admin_service_edit(request: Request, serviceid: int) -> HTMLResponse:
        db = request.app.state.db
        service = get_service(db, serviceid)
        if service is None:
            return HTMLResponse("Not found", status_code=404)
        return HTMLResponse(_render_edit_page(service))

    @app.post("/admin/services/{serviceid}")
    @login_required
    async def admin_service_update(
        request: Request,
        serviceid: int,
        pickup: str = Form(...),
        dropoff: str = Form(...),
        date: str = Form(...),
        pickup_time: str = Form(...),
        pax: int = Form(...),
        paxname: str = Form(...),
        paxphone: str = Form(...),
        subclass: str = Form(""),
        servicetype: str = Form(""),
        cartype: str = Form(""),
        price: float = Form(0),
        service_status: int = Form(2),
    ) -> RedirectResponse:
        db = request.app.state.db
        payload = {
            "pickup": pickup,
            "dropoff": dropoff,
            "date": date,
            "pickup_time": pickup_time,
            "pax": pax,
            "paxname": paxname,
            "paxphone": paxphone,
            "subclass": subclass,
            "servicetype": servicetype,
            "cartype": cartype,
            "price": price,
            "service_status": service_status,
        }
        update_service(db, serviceid, payload)
        return RedirectResponse(url="/admin/services", status_code=303)

    @app.api_route("/api/rest_api.php", methods=["GET", "POST"])
    async def rest_api(request: Request) -> JSONResponse:
        db = request.app.state.db
        params = dict(request.query_params)
        cmd = params.get("cmd", "")
        token = params.get("token", "")
        dominio = params.get("dominio", "")

        if not token or not dominio:
            return JSONResponse({"success": False, "error": "Missing token or dominio"})
        if not token_exists(db, token, dominio):
            return JSONResponse({"success": False, "error": "Invalid token or dominio"})

        if cmd == "cmd_read":
            start_date = params.get("start_date", "")
            if not start_date:
                return JSONResponse({"success": False, "error": "Missing start_date"})
            data = list_services(
                db,
                start_date=start_date,
                end_date=params.get("end_date"),
                subclass=params.get("subclass"),
                paxname=params.get("paxname"),
            )
            return JSONResponse({"success": True, "data": data, "error": ""})

        if cmd == "cmd_insert":
            payload = await _extract_payload(request)
            required_fields = [
                "pickup",
                "dropoff",
                "date",
                "pickup_time",
                "pax",
                "paxname",
                "paxphone",
            ]
            missing = [key for key in required_fields if not payload.get(key)]
            if missing:
                return JSONResponse(
                    {"success": False, "error": "Missing required fields: " + ", ".join(missing)}
                )
            serviceid = insert_service(db, payload)
            return JSONResponse({"success": True, "serviceid": serviceid, "error": ""})

        if cmd == "cmd_update":
            payload = await _extract_payload(request)
            serviceid_raw = payload.get("serviceid")
            if serviceid_raw is None:
                return JSONResponse({"success": False, "error": "Missing serviceid"})
            try:
                serviceid = int(serviceid_raw)
            except (TypeError, ValueError):
                return JSONResponse({"success": False, "error": "Invalid serviceid"})
            if not update_service(db, serviceid, payload):
                return JSONResponse({"success": False, "error": "Service not found"})
            return JSONResponse({"success": True, "error": ""})

        if cmd == "cmd_customer":
            vat = params.get("vat", "")
            if not vat:
                return JSONResponse({"success": False, "error": "Missing vat"})
            data = list_customers_by_vat(db, vat)
            return JSONResponse({"success": True, "data": data, "error": ""})

        if cmd == "cmd_driver":
            driverid_raw = params.get("driverid", "")
            try:
                driverid = int(driverid_raw)
            except ValueError:
                return JSONResponse({"success": False, "error": "Invalid driverid"})
            data = get_driver_by_id(db, driverid)
            return JSONResponse({"success": True, "data": data, "error": ""})

        return JSONResponse({"success": False, "error": "Unknown command"})


async def _extract_payload(request: Request) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                data.update(body)
        else:
            form = await request.form()
            data.update(dict(form))
    return data


def _base_html(content: str, title: str) -> str:
    return (
        "<!doctype html>"
        "<html><head>"
        f"<title>{title}</title>"
        "<meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<link "
        "href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' "
        "rel='stylesheet'>"
        "</head><body><div class='container py-4'>"
        f"{content}"
        "</div></body></html>"
    )


def _render_login_page(error: str = "") -> str:
    alert = (
        f"<div class='alert alert-danger' role='alert'>{error}</div>"
        if error
        else ""
    )
    body = (
        "<h1 class='h4 mb-3'>NCCGEST Mock Login</h1>"
        f"{alert}"
        "<form method='post' action='/admin/login' class='card p-3' style='max-width: 420px;'>"
        "<div class='mb-2'><label class='form-label'>Username</label>"
        "<input class='form-control' name='username' required /></div>"
        "<div class='mb-3'><label class='form-label'>Password</label>"
        "<input type='password' class='form-control' name='password' required /></div>"
        "<button class='btn btn-primary' type='submit'>Sign in</button>"
        "</form>"
    )
    return _base_html(body, "NCCGEST Mock Login")


def _render_services_page(items: Any) -> str:
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{item['id']}</td>"
            f"<td>{item['date']}</td>"
            f"<td>{item['time']}</td>"
            f"<td>{item.get('pickup_address', '')}</td>"
            f"<td>{item.get('dropoff_address', '')}</td>"
            f"<td>{item.get('paxname', '')}</td>"
            f"<td>{item.get('subclass', '')}</td>"
            "<td>"
            f"<a class='btn btn-sm btn-outline-primary' "
            f"href='/admin/services/{item['id']}'>Edit</a>"
            "</td>"
            "</tr>"
        )

    table_rows = "".join(rows) if rows else "<tr><td colspan='8'>No data</td></tr>"
    body = (
        "<div class='d-flex justify-content-between align-items-center mb-3'>"
        "<h1 class='h4 m-0'>Services</h1>"
        "<form method='post' action='/admin/logout'>"
        "<button class='btn btn-outline-secondary'>Logout</button>"
        "</form>"
        "</div>"
        "<table class='table table-striped table-bordered'>"
        "<thead><tr><th>ID</th><th>Date</th><th>Time</th><th>Pickup</th><th>Dropoff</th><th>Pax</th><th>Subclass</th><th></th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table>"
    )
    return _base_html(body, "NCCGEST Mock Services")


def _render_edit_page(service: Dict[str, Any]) -> str:
    body = (
        "<div class='d-flex justify-content-between align-items-center mb-3'>"
        f"<h1 class='h4 m-0'>Edit service #{service['id']}</h1>"
        "<a href='/admin/services' class='btn btn-outline-secondary'>Back</a>"
        "</div>"
        f"<form method='post' action='/admin/services/{service['id']}' class='card p-3'>"
        "<div class='row g-2'>"
        "<div class='col-md-4'><label class='form-label'>Pickup</label>"
        f"<input class='form-control' name='pickup' value='{service['pickup']}' required /></div>"
        "<div class='col-md-4'><label class='form-label'>Dropoff</label>"
        f"<input class='form-control' name='dropoff' value='{service['dropoff']}' required /></div>"
        "<div class='col-md-2'><label class='form-label'>Date</label>"
        f"<input class='form-control' name='date' value='{service['date']}' required /></div>"
        "<div class='col-md-2'><label class='form-label'>Time</label>"
        f"<input class='form-control' name='pickup_time' value='{service['time']}' required />"
        "</div>"
        "<div class='col-md-2'><label class='form-label'>Pax</label>"
        f"<input type='number' class='form-control' name='pax' value='{service['pax']}' required />"
        "</div>"
        "<div class='col-md-4'><label class='form-label'>Pax Name</label>"
        f"<input class='form-control' name='paxname' value='{service['paxname']}' required /></div>"
        "<div class='col-md-4'><label class='form-label'>Pax Phone</label>"
        f"<input class='form-control' name='paxphone' value='{service['paxphone']}' required />"
        "</div>"
        "<div class='col-md-2'><label class='form-label'>Subclass</label>"
        f"<input class='form-control' name='subclass' value='{service['subclass']}' /></div>"
        "<div class='col-md-3'><label class='form-label'>Service Type</label>"
        f"<input class='form-control' name='servicetype' value='{service['servicetype']}' /></div>"
        "<div class='col-md-3'><label class='form-label'>Car Type</label>"
        f"<input class='form-control' name='cartype' value='{service['cartype']}' /></div>"
        "<div class='col-md-2'><label class='form-label'>Price</label>"
        f"<input type='number' step='0.01' class='form-control' "
        f"name='price' value='{service['price']}' />"
        "</div>"
        "<div class='col-md-2'><label class='form-label'>Status</label>"
        f"<input type='number' class='form-control' "
        f"name='service_status' value='{service['service_status']}' />"
        "</div>"
        "</div>"
        "<div class='mt-3'><button class='btn btn-primary'>Save</button></div>"
        "</form>"
    )
    return _base_html(body, "Edit Service")
