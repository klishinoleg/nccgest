"""FastAPI app implementing a mock NCCGEST service."""

from __future__ import annotations

import sqlite3
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .seed import seed_if_empty
from .settings import MockSettings
from .storage import (
    connect,
    get_customer,
    get_driver,
    get_driver_by_id,
    get_service,
    init_schema,
    insert_service,
    list_customers,
    list_customers_by_vat,
    list_drivers,
    list_services,
    list_services_admin,
    token_exists,
    update_customer,
    update_driver,
    update_service,
)

SERVICE_ENUM_OPTIONS: Dict[str, list[tuple[str, str]]] = {
    "service_status": [("0", "Canceled"), ("1", "Waiting"), ("2", "Confirmed")],
    "cash": [("0", "Card/Invoice"), ("1", "Cash")],
    "servincassato": [("0", "Not paid"), ("1", "Partial"), ("2", "Full")],
    "incasso_serv": [
        ("0", "Not specified"),
        ("1", "C/C - Bancomat"),
        ("2", "Contanti"),
        ("3", "Incassato in ufficio"),
        ("4", "Bonifico"),
    ],
    "invoice_receipt": [("1", "Invoice"), ("2", "Receipt")],
    "pets": [("0", "No pets"), ("1", "Pets")],
}


def create_app(settings: Optional[MockSettings] = None) -> FastAPI:
    cfg = settings or MockSettings.from_env()
    app = FastAPI(title="NCCGEST Mock Service")
    app.add_middleware(SessionMiddleware, secret_key=cfg.session_secret)
    app.state.settings = cfg
    app.state.db = connect(cfg.db_path)
    _init_db(app.state.db, cfg)

    base_dir = Path(__file__).parent
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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

    @app.get("/")
    async def root(request: Request) -> Response:
        if request.session.get("logged_in"):
            return RedirectResponse(url="/admin/services", status_code=303)
        return RedirectResponse(url="/admin/login", status_code=303)

    @app.get("/admin/login")
    async def admin_login_page(request: Request) -> Response:
        return _tpl(request, "login.html", page_title="Login")

    @app.post("/admin/login")
    async def admin_login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
    ) -> Response:
        settings: MockSettings = request.app.state.settings
        if username == settings.login and password == settings.password:
            request.session["logged_in"] = True
            return RedirectResponse(url="/admin/services", status_code=303)
        return _tpl(request, "login.html", page_title="Login", error="Invalid credentials")

    @app.post("/admin/logout")
    async def admin_logout(request: Request) -> RedirectResponse:
        request.session.clear()
        return RedirectResponse(url="/admin/login", status_code=303)

    @app.get("/admin/services")
    @login_required
    async def admin_services(request: Request) -> Response:
        db = request.app.state.db
        items = list_services_admin(db)
        return _tpl(
            request,
            "services_list.html",
            page_title="Services",
            services=items,
            active_nav="services",
        )

    @app.get("/admin/services/{serviceid}")
    @login_required
    async def admin_service_edit(request: Request, serviceid: int) -> Response:
        db = request.app.state.db
        service = get_service(db, serviceid)
        if service is None:
            return Response("Not found", status_code=404)
        return _tpl(
            request,
            "service_edit.html",
            page_title="Edit Service",
            service=service,
            enum_options=SERVICE_ENUM_OPTIONS,
            active_nav="services",
        )

    @app.post("/admin/services/{serviceid}")
    @login_required
    async def admin_service_update(
        request: Request,
        serviceid: int,
    ) -> RedirectResponse:
        db = request.app.state.db
        form = await request.form()
        payload = dict(form)
        update_service(db, serviceid, payload)
        return RedirectResponse(url="/admin/services", status_code=303)

    @app.get("/admin/drivers")
    @login_required
    async def admin_drivers(request: Request) -> Response:
        db = request.app.state.db
        items = list_drivers(db)
        return _tpl(
            request,
            "drivers_list.html",
            page_title="Drivers",
            drivers=items,
            active_nav="drivers",
        )

    @app.get("/admin/drivers/{driverid}")
    @login_required
    async def admin_driver_edit(request: Request, driverid: int) -> Response:
        db = request.app.state.db
        driver = get_driver(db, driverid)
        if driver is None:
            return Response("Not found", status_code=404)
        return _tpl(
            request,
            "driver_edit.html",
            page_title="Edit Driver",
            driver=driver,
            active_nav="drivers",
        )

    @app.post("/admin/drivers/{driverid}")
    @login_required
    async def admin_driver_update(
        request: Request,
        driverid: int,
    ) -> RedirectResponse:
        db = request.app.state.db
        form = await request.form()
        payload = dict(form)
        update_driver(db, driverid, payload)
        return RedirectResponse(url="/admin/drivers", status_code=303)

    @app.get("/admin/customers")
    @login_required
    async def admin_customers(request: Request) -> Response:
        db = request.app.state.db
        items = list_customers(db)
        return _tpl(
            request,
            "customers_list.html",
            page_title="Customers",
            customers=items,
            active_nav="customers",
        )

    @app.get("/admin/customers/{customerid}")
    @login_required
    async def admin_customer_edit(request: Request, customerid: int) -> Response:
        db = request.app.state.db
        customer = get_customer(db, customerid)
        if customer is None:
            return Response("Not found", status_code=404)
        return _tpl(
            request,
            "customer_edit.html",
            page_title="Edit Customer",
            customer=customer,
            active_nav="customers",
        )

    @app.post("/admin/customers/{customerid}")
    @login_required
    async def admin_customer_update(request: Request, customerid: int) -> RedirectResponse:
        db = request.app.state.db
        form = await request.form()
        payload = dict(form)
        update_customer(db, customerid, payload)
        return RedirectResponse(url="/admin/customers", status_code=303)

    @app.api_route("/api/rest_api.php", methods=["GET", "POST"])
    async def rest_api(request: Request) -> JSONResponse:
        db = request.app.state.db
        params = dict(request.query_params)
        cmd = params.get("cmd", "")
        token = params.get("token", "")
        dominio = params.get("dominio", "")

        if not token or not dominio:
            return JSONResponse({"success": False, "error": "Missing token or dominio"})
        cmd_token_type = {
            "cmd_read": "customer",
            "cmd_insert": "customer",
            "cmd_update": "customer",
            "cmd_customer": "master",
            "cmd_driver": "master",
        }.get(cmd)
        if not token_exists(db, token, dominio, required_token_type=cmd_token_type):
            return JSONResponse({"success": False, "error": "Invalid Token"})

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


def _tpl(request: Request, template_name: str, **context: Any) -> Response:
    templates: Jinja2Templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )


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
