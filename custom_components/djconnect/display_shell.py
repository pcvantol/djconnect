"""Public empty B shell: generic app code, never display or owner authority."""
from __future__ import annotations

import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .display_origin import selected_ha_origin
from .display_transport import SECURITY_HEADERS


class _InlineHashes(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script" and not any(key == "src" for key, _value in attrs):
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


def shell_csp(html, origin):
    parser = _InlineHashes()
    parser.feed(html)
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
              for script in parser.scripts]
    return ("default-src 'none'; script-src " + " ".join(hashes) + "; "
        "style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self' " + origin.replace("https:", "wss:", 1)
        + "; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'; "
        "frame-src 'none'; worker-src 'none'; media-src 'none'")


class DisplayShellView(HomeAssistantView):
    url = "/djconnect/vibecast/display"
    name = "api:djconnect:display:shell"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        origin = selected_ha_origin(self.hass)
        supplied = tuple(request.headers.getall("Origin", []))
        if (origin is None or not request.secure or request.query_string
                or (supplied and supplied != (origin,))):
            return web.json_response({"success": False, "error": "display_origin_denied"},
                                     status=403, headers=SECURITY_HEADERS)
        # Public top-level GET normally has no Origin. It allocates no state and
        # contains no installation/Profile/Session, claim, grant or owner token.
        page = await self.hass.async_add_executor_job(
            (Path(__file__).parent / "vibecast_display.html").read_text)
        if selected_ha_origin(self.hass) != origin:
            return web.json_response({"success": False, "error": "display_context_changed"},
                                     status=409, headers=SECURITY_HEADERS)
        return web.Response(text=page, content_type="text/html", headers={**SECURITY_HEADERS,
            "Content-Security-Policy": shell_csp(page, origin), "X-Frame-Options": "DENY",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()"})
