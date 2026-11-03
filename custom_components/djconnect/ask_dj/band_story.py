"""Source-proved band presentation; no membership facts or playback grants."""
from dataclasses import dataclass
from datetime import UTC, datetime
import re
from urllib.parse import quote

from .public_research import PublicSource


@dataclass(frozen=True)
class BandIdentity:
    subject: str
    qid: str
    source: PublicSource

    def current(self):
        try:
            start = datetime.fromisoformat(self.source.fetched_at)
            end = datetime.fromisoformat(self.source.expires_at)
            now = datetime.now(UTC)
            return bool(start.tzinfo is not None and end.tzinfo is not None
                        and start <= now < end and (end - start).total_seconds() <= 3600)
        except (TypeError, ValueError):
            return False


def band_identity(sources, subject):
    """A canonical original group lead, never a name slot or a model label."""
    from .biographical_dates import _group_source
    if not isinstance(subject, str) or not subject or type(sources) not in (tuple, list):
        return None
    original = [s for s in sources if type(s) is PublicSource and s.provider == "Wikipedia"]
    if not original or len({s.entity_id for s in original}) != 1:
        return None
    primary = original[0]
    if (not re.fullmatch(r"Q[1-9][0-9]*", primary.entity_id)
            or primary.language not in {"en", "nl", "de", "fr", "es"}
            or primary.url != "https://" + primary.language + ".wikipedia.org/wiki/"
                + quote(primary.title.replace(" ", "_"), safe="")
            or not _group_source(primary.model_data(), subject)):
        return None
    identity = BandIdentity(subject, primary.entity_id, primary)
    return identity if identity.current() else None


# Public pictures use the existing proxy endpoint, with retained validated bytes.
# A capability is a short public-photo display lease, never a Session/device grant.
PHOTO_PREFIX = "band-"
MAX_ASSETS = 32
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 2 * 1024 * 1024
PHOTO_SECONDS = 300


class BandImages:
    def __init__(self, hass):
        from homeassistant.const import EVENT_HOMEASSISTANT_STOP
        self.hass, self.assets, self.watchers = hass, {}, {}
        self.closed = False
        self.unsubscribe = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.close)

    def drop(self, token):
        asset = self.assets.pop(token, None)
        if asset is not None:
            asset["timer"].cancel()
            asset.clear()  # Release original pixels and minimal authority references.

    def drop_entry(self, entry_id):
        for token, asset in list(self.assets.items()):
            if entry_id in asset["entry_ids"]:
                self.drop(token)
        self.watchers.pop(entry_id, None)

    def invalidate_history(self, history, scopes):
        for token, asset in list(self.assets.items()):
            if asset["history"] is history and asset["scope"] in scopes:
                self.drop(token)

    def for_request(self, history, scope, request_id):
        from copy import deepcopy
        from ..const import API_IMAGE_PROXY_BASE
        if not isinstance(request_id, str) or not request_id:
            return []
        for token in list(self.assets):
            asset = self.get(token)
            if (asset is not None and asset["history"] is history and asset["scope"] == scope
                    and asset["request_id"] == request_id):
                url = API_IMAGE_PROXY_BASE + "/" + token
                return [{"url": url, "thumbnail_url": url, **deepcopy(asset["metadata"])}]
        return []

    def close(self, _event=None):
        if self.closed:
            return
        self.closed = True
        for token in list(self.assets):
            self.drop(token)
        self.watchers.clear()
        unsubscribe, self.unsubscribe = self.unsubscribe, None
        if unsubscribe is not None:
            unsubscribe()

    def get(self, token):
        import time
        asset = self.assets.get(token)
        if asset is None:
            return None
        try:
            valid = (not self.closed and time.time() < asset["wall_deadline"]
                     and time.monotonic() < asset["mono_deadline"] and asset["allowed"]())
        except Exception:  # No exception payload, provider text or credentials escape.
            valid = False
        if not valid:
            self.drop(token)  # An observed denial is terminal, including an observed ABA.
            return None
        return asset

    def commit(self, *, body, mime, allowed, runtime, wall_deadline, mono_deadline, metadata, provider_entry, history, scope, request_id):
        import secrets
        import time
        from ..const import API_IMAGE_PROXY_BASE
        for token in list(self.assets):
            self.get(token)
        from copy import deepcopy
        entries = {getattr(e, "entry_id", ""): e for e in (getattr(runtime, "entry", None), provider_entry)}
        if (len(entries) != len({id(e) for e in (getattr(runtime, "entry", None), provider_entry)})
                or any(not k or e is None or not callable(getattr(e, "async_on_unload", None))
                       or (k in self.watchers and self.watchers[k] is not e) for k, e in entries.items())
                or self.closed or not allowed() or time.time() >= wall_deadline
                or time.monotonic() >= mono_deadline
                or type(body) is not bytes or not 0 < len(body) <= MAX_IMAGE_BYTES
                or mime not in {"image/jpeg", "image/png", "image/webp"}
                or len(self.assets) >= MAX_ASSETS
                or sum(len(a["body"]) for a in self.assets.values()) + len(body) > MAX_TOTAL_BYTES
                or len(set(self.watchers) | set(entries)) > MAX_ASSETS):
            return ""
        for entry_id, entry in entries.items():
            if entry_id not in self.watchers:
                self.watchers[entry_id] = entry
                entry.async_on_unload(lambda entry_id=entry_id: self.drop_entry(entry_id))
        token = PHOTO_PREFIX + secrets.token_urlsafe(24)
        asset = {"body": body, "mime": mime, "allowed": allowed, "runtime": runtime,
                 "entry_ids": tuple(entries), "wall_deadline": wall_deadline, "mono_deadline": mono_deadline,
                 "metadata": deepcopy(metadata), "history": history, "scope": scope, "request_id": request_id}
        asset["timer"] = self.hass.loop.call_later(
            max(0, min(wall_deadline - time.time(), mono_deadline - time.monotonic())), self.drop, token)
        self.assets[token] = asset
        return API_IMAGE_PROXY_BASE + "/" + token


def images(hass):
    from ..const import DOMAIN
    owner = hass.data.setdefault(DOMAIN, {})
    if "public_band_images" not in owner:
        owner["public_band_images"] = BandImages(hass)
    return owner["public_band_images"]


async def prepare_photo(hass, runtime, turn, identity):
    """One optional licensed image; original sources/owner/deadlines never renew."""
    import asyncio
    import time
    from .. import artist_photo
    from ..discovery_artwork import privacy_scope
    from ..image_proxy import session_images
    from ..session_artwork import _decoded_size
    from ..session_conversation import history_grant_revision
    from ..persistence.content_deletion import request_deleted_now
    from ..const import DOMAIN

    wall, mono = time.time(), time.monotonic()  # Before the first await.
    authority = turn.reply_source_authority
    if (type(identity) is not BandIdentity or not identity.current()
            or not callable(authority) or not authority() or not turn.scope.startswith("profile:")):
        return []
    history, scope = turn.history, turn.scope
    original_store = getattr(history, "_store", None)
    source = turn.reply_source_context or {}
    provider_entry_id = source.get("provider_entry_id")
    provider_entry = (hass.config_entries.async_get_entry(provider_entry_id)
        if isinstance(provider_entry_id, str) and provider_entry_id else None)
    if (hass.data.get(DOMAIN, {}).get("ask_dj_history_manager") is not history
            or getattr(history, "hass", None) is not hass or original_store is None
            or not getattr(history, "_loaded", False) or provider_entry is None):
        return []
    profile = scope.removeprefix("profile:")
    original_privacy = history.media_privacy_revision(scope)
    original_grant = history_grant_revision(hass, profile)
    original_policy = privacy_scope(runtime)
    request_id = turn.client_id
    source_requests = frozenset(turn.source_request_hashes)
    wall_deadline = min(wall + PHOTO_SECONDS, datetime.fromisoformat(identity.source.expires_at).timestamp())
    mono_deadline = mono + max(0, wall_deadline - wall)

    def allowed():
        service = hass.data.get(DOMAIN, {}).get("persistence_service")
        withdrawn = getattr(service, "content_request_fences", {}).get(profile, set())
        return bool(authority() and identity.current()
                    and hass.data.get(DOMAIN, {}).get("ask_dj_history_manager") is history
                    and getattr(history, "_store", None) is original_store and history._loaded
                    and hass.config_entries.async_get_entry(provider_entry_id) is provider_entry
                    and history.media_privacy_revision(scope) == original_privacy
                    and history_grant_revision(hass, profile) == original_grant
                    and privacy_scope(runtime) == original_policy
                    and not request_deleted_now(hass, profile, request_id)
                    and not source_requests.intersection(withdrawn))

    async def guard():
        await turn.guard()
        if (not allowed() or time.time() >= wall_deadline or time.monotonic() >= mono_deadline):
            raise artist_photo.PhotoUnavailable("source_withdrawn")

    async def decode(body):
        await guard()
        try:
            result = await session_images(hass).decode(_decoded_size, body)
        except ValueError:
            raise artist_photo.PhotoUnavailable("unsafe_image") from None
        await guard()
        return result

    try:
        async with asyncio.timeout_at(mono + 8):
            await guard()
            body, mime, photo = await artist_photo.fetch(hass, identity.qid, guard=guard, decode=decode)
            await guard()
        if type(photo) is not artist_photo.Candidate or not artist_photo.thumbnail_url(photo.url, photo.original_url):
            return []
        # The fetcher has checked identity, licence, MIME, dimensions and pixels.
        # Retain exactly those bytes; the public GET never re-fetches the URL.
        metadata = {"title": identity.subject, "subtitle": photo.attribution, "kind": "artist_image",
                    "source": "wikimedia_commons", "subject": {"type": "band", "wikidata_id": identity.qid},
                    "attribution": photo.metadata(), "width": photo.width, "height": photo.height,
                    "expires_at": datetime.fromtimestamp(wall_deadline, UTC).isoformat(),
                    "cache_policy": "private,no-store", "requires_device_auth": False,
                    "usage_basis": "licensed_public_photo_temporary_owner_capability"}
        url = images(hass).commit(body=body, mime=mime, allowed=allowed, runtime=runtime,
            wall_deadline=wall_deadline, mono_deadline=mono_deadline, metadata=metadata, provider_entry=provider_entry,
            history=history, scope=scope, request_id=request_id)
        return [projection_for_url(hass, url)] if url else []
    except (artist_photo.PhotoUnavailable, TimeoutError, OSError):
        return []


def projection_for_url(hass, url):
    """Only this typed original registry supplies public attribution metadata."""
    from copy import deepcopy
    from ..const import API_IMAGE_PROXY_BASE, DOMAIN
    prefix = API_IMAGE_PROXY_BASE + "/"
    if not isinstance(url, str) or not url.startswith(prefix):
        return None
    token = url[len(prefix):]
    if not re.fullmatch(r"band-[A-Za-z0-9_-]{32}", token):
        return None
    registry = hass.data.get(DOMAIN, {}).get("public_band_images")
    asset = registry.get(token) if type(registry) is BandImages else None
    return {"url": url, "thumbnail_url": url, **deepcopy(asset["metadata"])} if asset else None


async def image_response(hass, request, token):
    """Deliver only the original admitted pixels, without any network operation."""
    from aiohttp import web
    from ..const import DOMAIN
    from ..request_auth import authorize_runtime_device_request
    if not re.fullmatch(r"band-[A-Za-z0-9_-]{32}", token):
        return web.Response(status=404)
    registry = hass.data.get(DOMAIN, {}).get("public_band_images")
    asset = registry.get(token) if type(registry) is BandImages else None
    if asset is None:
        return web.Response(status=404)
    keys = ("Authorization", "X-DJConnect-Device-ID", "X-DJConnect-Client-Type")
    headers = request.headers
    if any(k in headers for k in keys):
        duplicate = any(len(headers.getall(k, [])) > 1 for k in keys) if hasattr(headers, "getall") else False
        if duplicate or not authorize_runtime_device_request(asset["runtime"], headers,
                headers.get("X-DJConnect-Device-ID"), headers.get("X-DJConnect-Client-Type")):
            return web.Response(status=401)
    # Last no-await validation. Expiry/withdrawal scrubs the original lease.
    if registry.get(token) is not asset:
        return web.Response(status=404)
    return web.Response(body=asset["body"], content_type=asset["mime"],
        headers={"Cache-Control": "private, no-store", "Content-Length": str(len(asset["body"]))})
