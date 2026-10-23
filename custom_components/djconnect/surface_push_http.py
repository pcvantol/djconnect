"""Closed owner surface routes; no root/purpose-token import or app fallback."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .surface_push_contract import BASE, IDENTIFIER, SurfacePushError, require, validate_registration
from .surface_push_service import now_ms
from .surface_push_wire import canonical, safe_integer
from .transport_operations import OperationError

HEADERS = {"Cache-Control":"no-store","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff"}
LIMIT = 16384
COMMON = {"contract_version","device_id","client_type","session_id"}


def parse(raw):
    def pairs(values):
        result = {}
        for key,value in values:
            require(key not in result,"invalid_request")
            result[key] = value
        return result
    def constant(_):
        raise SurfacePushError("invalid_request")
    try:
        value = json.loads(raw.decode("utf-8",errors="strict"),object_pairs_hook=pairs,parse_constant=constant)
    except (ValueError,UnicodeError):
        raise SurfacePushError("invalid_request") from None
    require(type(value) is dict,"invalid_request")
    return value


def validate(kind, data):
    if kind in {"register", "context"}:
        require(type(data) is dict, "invalid_request")
        require(not (type(data.get("contract_version")) is int and data["contract_version"] == 1),
            "surface_context_required", 409)
        require(type(data.get("contract_version")) is int and data["contract_version"] == 2, "invalid_request")
        if kind == "register":
            require("context_handle" in data and type(data["context_handle"]) is str
                and data["context_handle"].startswith("djcctx_") and len(data["context_handle"]) == 50,
                "surface_context_required", 409)
            legacy = {k:v for k,v in data.items() if k != "context_handle"}
            legacy["contract_version"] = 1
            return validate_registration(legacy,now_ms=now_ms())
        require(set(data) == COMMON | {"operation_id"}, "invalid_request")
        for key in COMMON - {"contract_version"}:
            require(type(data[key]) is str and IDENTIFIER.fullmatch(data[key]), "invalid_request")
        from .transport_operations import operation_created_ms
        operation_created_ms(data["operation_id"])
        return None
    expected = ({"contract_version","registration_id"} if kind=="read" else
        COMMON | ({"registration_id"} if kind=="status" else
            {"operation_id","expected_registration"} if kind=="revoke" else set()))
    require(type(data) is dict and set(data)==expected and type(data["contract_version"]) is int
        and data["contract_version"]==1,"invalid_request")
    for key in expected-{"contract_version","expected_registration"}:
        require(type(data[key]) is str and IDENTIFIER.fullmatch(data[key]),"invalid_request")
    if kind=="revoke":
        coordinate = data["expected_registration"]
        require(type(coordinate) is dict and set(coordinate)=={"registration_id","generation","revision"}
            and all(type(coordinate[k]) is str and IDENTIFIER.fullmatch(coordinate[k])
                for k in ("registration_id","generation"))
            and safe_integer(coordinate["revision"],1),"invalid_request")
    return None


async def handle(hass, kind, data, headers):
    intent = validate(kind,data)
    service = hass.data.get("djconnect",{}).get("surface_push_service")
    require(service is not None and not service.closed,"surface_unavailable",503)
    if kind=="read":
        authorization = headers.get("Authorization","")
        require(type(authorization) is str and re.fullmatch(r"Bearer djcsurface_[A-Za-z0-9_-]{43}",authorization),
            "surface_read_unauthorized",401)
        return service.registry.read(data["registration_id"],authorization[7:]),200
    if kind == "context":
        return await service.run(service.contexts.acquire(data, headers)), 200
    if kind == "register":
        return await service.run(service.contexts.register(data["context_handle"], intent, headers)), 200
    admission = await service.admission(data, headers)
    if kind=="revoke":
        result = await service.run(service.registry.revoke(admission,data["expected_registration"],
            operation_id=data["operation_id"],digest=hashlib.sha256(canonical(data).encode()).hexdigest()))
        service.collect_signals()
        return result,200
    return service.registry.status(admission,data["registration_id"]),200


class SurfacePushView(HomeAssistantView):
    requires_auth = False  # Exact paired or separate background credential in handle.

    def __init__(self, hass, kind):
        self.hass,self.kind = hass,kind
        self.url = BASE+"/"+kind
        self.name = "api:djconnect:push:surface:"+kind

    def register(self, hass, app, router):
        router.add_route("POST",self.url,self.post)
        router.add_route("*",self.url,self.unsupported)

    @staticmethod
    def response(value,status=200,extra=None):
        return web.Response(text=json.dumps(value,allow_nan=False),status=status,content_type="application/json",
            headers={**HEADERS,**(extra or {})})

    async def unsupported(self,request):
        return self.response({"success":False,"error":"method_not_allowed"},405,{"Allow":"POST"})

    async def post(self,request):
        raw = bytearray()
        data = None
        try:
            require(not self.hass.is_stopping,"surface_unavailable",503)
            require(not request.query_string,"invalid_request")
            require(request.content_type=="application/json" and
                (request.charset or "utf-8").lower() in {"utf-8","utf8"}
                and request.headers.get("Content-Encoding","identity").lower()=="identity",
                "unsupported_media_type",415)
            require(request.content_length is None or request.content_length<=LIMIT,"request_too_large",413)
            async with asyncio.timeout(5):
                while len(raw)<=LIMIT:
                    chunk = await request.content.read(min(2048,LIMIT+1-len(raw)))
                    if not chunk:
                        break
                    raw.extend(chunk)
            require(len(raw)<=LIMIT,"request_too_large",413)
            data = parse(raw)
            raw.clear()
            value,status = await handle(self.hass,self.kind,data,request.headers)
            return self.response(value,status)
        except (SurfacePushError,OperationError) as error:
            return self.response({"success":False,"error":error.code},error.status)
        except asyncio.CancelledError:
            raise
        except Exception:  # No input/upstream/credential/body/exception logging.
            return self.response({"success":False,"error":"surface_unavailable"},503)
        finally:
            raw.clear()
            if data is not None:
                data.clear()  # Drop references, not a secure-erasure claim.


def surface_views(hass):
    return [SurfacePushView(hass,kind) for kind in ("context","register","revoke","status","read")]
