"""Type aliases for request/response payloads."""

from typing import Any, Dict, List, TypedDict

JSONDict = Dict[str, Any]
JSONList = List[Any]


class Passenger(TypedDict, total=False):
    name: str
    phone: str


class InsertServicePayload(TypedDict, total=False):
    pickup: str
    pickup_address: str
    dropoff: str
    dropoff_address: str
    date: str
    pickup_time: str
    dropoff_date: str
    dropoff_time: str
    flight_train: str
    flight_train_origin: str
    pax: int
    bags: int
    pets: int
    child_seat_1: int
    child_seat_2: int
    child_seat_3: int
    service_note: str
    cartype: str
    vehicle_plate: str
    servicetype: str
    paxname: str
    paxphone: str
    paxmail: str
    price: float
    comm_cliente: float
    cash: int
    subclass: str
    impincassato: float
    servincassato: float
    incasso_serv: float
    invoice_receipt: int
    number_invoice_receipt: str
    ids_supplier: int
    ids_driver: int
    ids_agente: int
    ids_ccp: int
    external_driver: str
    comm_driver: float
    comm_agent: float
    operator_note: str
    service_status: int


class UpdateServicePayload(InsertServicePayload, total=False):
    update_note: int
    internal_driverid: int
    smallbags: int
