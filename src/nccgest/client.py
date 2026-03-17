"""Sync and async clients for NCCGEST REST API."""

from __future__ import annotations

from typing import Any, List, Optional

import httpx

from .exceptions import NCCGestAPIError, NCCGestError, NCCGestHTTPError, NCCGestResponseError
from .types import (
    CustomerDataItem,
    DriverDataItem,
    InsertServicePayload,
    JSONDict,
    ReadServiceItem,
    UpdateServicePayload,
)

DEFAULT_BASE_URL = "https://api.nccgest.com/api/rest_api.php"


def _build_params(domain: str, cmd: str, token: Optional[str] = None, **kwargs: Any) -> JSONDict:
    params: JSONDict = {"dominio": domain, "cmd": cmd}
    if token is not None:
        params["token"] = token
    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
    return params


def _parse_response(response: httpx.Response) -> JSONDict:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise NCCGestHTTPError(str(exc), status_code=exc.response.status_code) from exc
    except httpx.HTTPError as exc:
        raise NCCGestHTTPError(str(exc)) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise NCCGestResponseError("Response is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise NCCGestResponseError("Unexpected JSON payload shape. Expected object.")

    if payload.get("success") is False:
        raise NCCGestAPIError(str(payload.get("error") or "Unknown API error."), response=payload)

    return payload


class NCCGestClient:
    """Synchronous NCCGEST API client."""

    def __init__(
        self,
        domain: str,
        token: Optional[str] = None,
        *,
        customer_token: Optional[str] = None,
        master_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.domain = domain
        # Backward compatibility: if only `token` is provided, it is used for both token types.
        self.customer_token = customer_token or token
        self.master_token = master_token or token
        self.base_url = base_url
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "NCCGestClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def read_services(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        *,
        subclass: Optional[str] = None,
        paxname: Optional[str] = None,
    ) -> List[ReadServiceItem]:
        params = _build_params(
            self.domain,
            "cmd_read",
            token=self._require_token("customer"),
            start_date=start_date,
            end_date=end_date,
            subclass=subclass,
            paxname=paxname,
        )
        response = self._client.get(self.base_url, params=params)
        payload = _parse_response(response)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise NCCGestResponseError("Expected `data` to be a list.")
        return data

    def insert_service(self, service: InsertServicePayload) -> int:
        body: JSONDict = dict(service)
        body["token"] = self._require_token("customer")
        params = _build_params(self.domain, "cmd_insert", token=self._require_token("customer"))
        response = self._client.post(self.base_url, params=params, json=body)
        payload = _parse_response(response)
        service_id = payload.get("serviceid")
        if service_id is None:
            raise NCCGestResponseError("Missing `serviceid` in insert response.")
        try:
            return int(service_id)
        except (TypeError, ValueError) as exc:
            raise NCCGestResponseError("`serviceid` is not an integer.") from exc

    def update_service(self, serviceid: int, service: UpdateServicePayload) -> None:
        body: JSONDict = dict(service)
        body["serviceid"] = serviceid
        body["token"] = self._require_token("customer")
        params = _build_params(self.domain, "cmd_update", token=self._require_token("customer"))
        response = self._client.post(self.base_url, params=params, json=body)
        _parse_response(response)

    def get_customer_data(self, vat: str) -> List[CustomerDataItem]:
        params = _build_params(
            self.domain,
            "cmd_customer",
            token=self._require_token("master"),
            vat=vat,
        )
        response = self._client.get(self.base_url, params=params)
        payload = _parse_response(response)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise NCCGestResponseError("Expected `data` to be a list.")
        return data

    def get_driver_data(self, driverid: int) -> List[DriverDataItem]:
        params = _build_params(
            self.domain,
            "cmd_driver",
            token=self._require_token("master"),
            driverid=driverid,
        )
        response = self._client.get(self.base_url, params=params)
        payload = _parse_response(response)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise NCCGestResponseError("Expected `data` to be a list.")
        return data

    def _require_token(self, token_type: str) -> str:
        if token_type == "customer":
            if not self.customer_token:
                raise NCCGestError(
                    "Customer token is required for cmd_read/cmd_insert/cmd_update. "
                    "Pass `customer_token=...` (or `token=...` for backward compatibility)."
                )
            return self.customer_token
        if token_type == "master":
            if not self.master_token:
                raise NCCGestError(
                    "Master token is required for cmd_customer/cmd_driver. "
                    "Pass `master_token=...` (or `token=...` for backward compatibility)."
                )
            return self.master_token
        raise NCCGestError("Unknown token type: " + token_type)


class AsyncNCCGestClient:
    """Asynchronous NCCGEST API client."""

    def __init__(
        self,
        domain: str,
        token: Optional[str] = None,
        *,
        customer_token: Optional[str] = None,
        master_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.domain = domain
        # Backward compatibility: if only `token` is provided, it is used for both token types.
        self.customer_token = customer_token or token
        self.master_token = master_token or token
        self.base_url = base_url
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncNCCGestClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def read_services(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        *,
        subclass: Optional[str] = None,
        paxname: Optional[str] = None,
    ) -> List[ReadServiceItem]:
        params = _build_params(
            self.domain,
            "cmd_read",
            token=self._require_token("customer"),
            start_date=start_date,
            end_date=end_date,
            subclass=subclass,
            paxname=paxname,
        )
        response = await self._client.get(self.base_url, params=params)
        payload = _parse_response(response)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise NCCGestResponseError("Expected `data` to be a list.")
        return data

    async def insert_service(self, service: InsertServicePayload) -> int:
        body: JSONDict = dict(service)
        body["token"] = self._require_token("customer")
        params = _build_params(self.domain, "cmd_insert", token=self._require_token("customer"))
        response = await self._client.post(self.base_url, params=params, json=body)
        payload = _parse_response(response)
        service_id = payload.get("serviceid")
        if service_id is None:
            raise NCCGestResponseError("Missing `serviceid` in insert response.")
        try:
            return int(service_id)
        except (TypeError, ValueError) as exc:
            raise NCCGestResponseError("`serviceid` is not an integer.") from exc

    async def update_service(self, serviceid: int, service: UpdateServicePayload) -> None:
        body: JSONDict = dict(service)
        body["serviceid"] = serviceid
        body["token"] = self._require_token("customer")
        params = _build_params(self.domain, "cmd_update", token=self._require_token("customer"))
        response = await self._client.post(self.base_url, params=params, json=body)
        _parse_response(response)

    async def get_customer_data(self, vat: str) -> List[CustomerDataItem]:
        params = _build_params(
            self.domain,
            "cmd_customer",
            token=self._require_token("master"),
            vat=vat,
        )
        response = await self._client.get(self.base_url, params=params)
        payload = _parse_response(response)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise NCCGestResponseError("Expected `data` to be a list.")
        return data

    async def get_driver_data(self, driverid: int) -> List[DriverDataItem]:
        params = _build_params(
            self.domain,
            "cmd_driver",
            token=self._require_token("master"),
            driverid=driverid,
        )
        response = await self._client.get(self.base_url, params=params)
        payload = _parse_response(response)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise NCCGestResponseError("Expected `data` to be a list.")
        return data

    def _require_token(self, token_type: str) -> str:
        if token_type == "customer":
            if not self.customer_token:
                raise NCCGestError(
                    "Customer token is required for cmd_read/cmd_insert/cmd_update. "
                    "Pass `customer_token=...` (or `token=...` for backward compatibility)."
                )
            return self.customer_token
        if token_type == "master":
            if not self.master_token:
                raise NCCGestError(
                    "Master token is required for cmd_customer/cmd_driver. "
                    "Pass `master_token=...` (or `token=...` for backward compatibility)."
                )
            return self.master_token
        raise NCCGestError("Unknown token type: " + token_type)
