"""Passive role discovery. No positive producer is selected in this increment."""
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import API_BASE
from .surface_registration import ROLES, RegistrationReadError, observe_pair

_CLOSED = b'{"version":1,"state":"UNAVAILABLE"}'
_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff"}


class SurfaceRegistrationStateView(HomeAssistantView):
    requires_auth = False  # Exact current ordinary device bearer below.

    def __init__(self, hass, role):
        if role not in ROLES:
            raise ValueError("invalid_role")
        self.hass = hass
        self.url = API_BASE + "/surface_registration/" + role + "/state"
        self.name = "api:djconnect:surface-registration:" + role + ":state"

    def register(self, hass, app, router):
        router.add_route("GET", self.url, self.get)
        router.add_route("*", self.url, self.unsupported)

    @staticmethod
    def response(status, *, method=False):
        headers = {**_HEADERS, **({"Allow": "GET"} if method else {})}
        return web.Response(body=_CLOSED, status=status, content_type="application/json", headers=headers)

    async def unsupported(self, request):
        return self.response(405, method=True)

    async def get(self, request):
        try:
            if ("?" in request.raw_path or request.body_exists or request.can_read_body
                    or request.headers.get("Transfer-Encoding") is not None
                    or request.content_length not in (None, 0)):
                raise RegistrationReadError(400)
            observation = observe_pair(self.hass, request.headers)
            # No await between final snapshot comparison and serialization.
            # An ordinary pair is NOT a qualified purpose-store acknowledgement.
            if not observation.current(self.hass):
                raise RegistrationReadError(503)
            return self.response(503)
        except RegistrationReadError as error:
            return self.response(error.status)
        except Exception:  # Never log headers, tokens, coordinates or exceptions.
            return self.response(503)


def registration_views(hass):
    return [SurfaceRegistrationStateView(hass, role) for role in ROLES]
