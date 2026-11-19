"""Paired pure Help observation; never a suggestion execution endpoint."""
import json

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import API_BASE


class HelpContextView(HomeAssistantView):
    url = API_BASE + "/ask_dj/help-context"
    name = "api:djconnect:ask-dj:help-context"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        from .ask_dj.help_observation import decode_query, observe
        try:
            # raw_path retains escapes; request.query has already collapsed or
            # decoded information needed for duplicate/encoding rejection.
            raw = request.raw_path.partition("?")[2].encode("ascii", errors="strict")
            query = decode_query(raw, has_body=request.body_exists or request.can_read_body)
        except (ValueError, UnicodeError):
            return self._response({"error": "invalid_request"}, 400)
        try:
            result = observe(self.hass, request.headers, query)
        except PermissionError:
            return self._response({"error": "unauthorized"}, 401)
        except Exception:
            # Unknown authorization is never an echo of a private subject.
            return self._response({"error": "observation_unavailable"}, 503)
        return self._response(result, 200)

    @staticmethod
    def _response(result, status):
        wire = json.dumps(result, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        from .ask_dj.help_observation import ObservedResponse
        if isinstance(result, ObservedResponse) and not result.final_check():
            wire = json.dumps(result.closed(), ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(wire.encode("ascii")) > 16384:
            wire, status = '{"error":"observation_unavailable"}', 503
        return web.Response(text=wire, status=status, content_type="application/json",
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                     "X-Content-Type-Options": "nosniff"})
