"""Send DJ responses to the DJConnect device speaker/display."""

from __future__ import annotations

import logging
import secrets
import time
import weakref
from dataclasses import dataclass, field
from typing import Any

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_TTS_BASE,
    CONF_DJ_RESPONSE_ENABLED,
    CONF_DJ_RESPONSE_TTL_SECONDS,
    DEFAULT_DJ_RESPONSE_ENABLED,
    DEFAULT_DJ_RESPONSE_TTL_SECONDS,
    DOMAIN,
)
from .ha_urls import async_ha_local_url
from .tts import UnsupportedTtsAudioError, TtsAudio, create_tts_audio

_LOGGER = logging.getLogger(__name__)


class PrivateSpeechSource:
    """Callback-only lifecycle metadata in the existing temporary audio owner."""

    def __init__(self, hass, validate, *, expires_at, session_id=None, entry_id=None):
        self.hass, self.validate = hass, validate
        self.expires_at, self.session_id = expires_at, session_id
        self.entry_id = entry_id
        domain = hass.data.setdefault(DOMAIN, {})
        self.epoch = domain.setdefault("tts_audio_authority_revision", 0)
        self.callbacks = []
        self.timer = None
        self.withdrawn = False
        sources = domain.setdefault("tts_audio_sources", weakref.WeakValueDictionary())
        if len(sources) >= 256:
            raise ValueError("speech_capacity")
        sources[id(self)] = self

    def __call__(self):
        domain = self.hass.data.get(DOMAIN, {})
        try:
            if (self.withdrawn or time.time() >= self.expires_at
                    or domain.get("tts_audio_authority_revision") != self.epoch):
                raise PermissionError("speech_source_withdrawn")
            self.validate()
        except Exception:
            self.withdraw()
            raise

    def withdraw(self):
        self.withdrawn = True
        self._unwatch()
        callbacks, self.callbacks = self.callbacks, []
        for callback in callbacks:
            try:
                callback()
            except Exception:
                _LOGGER.debug("Private speech withdrawal callback failed")

    def _unwatch(self):
        self.hass.data.get(DOMAIN, {}).get("tts_audio_source_watches", {}).pop(id(self), None)
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def on_withdraw(self, callback):
        import asyncio
        self()
        watches = self.hass.data.setdefault(DOMAIN, {}).setdefault("tts_audio_source_watches", {})
        if id(self) not in watches:
            if len(watches) >= 64:
                raise ValueError("speech_capacity")
            watches[id(self)] = self
            self.timer = asyncio.get_running_loop().call_later(
                max(0, self.expires_at - time.time()), self.withdraw)
        self.callbacks.append(callback)
        def remove():
            if callback in self.callbacks:
                self.callbacks.remove(callback)
            if not self.callbacks:
                self._unwatch()
        return remove


def invalidate_private_speech_sources(hass, *, session_id=None, entry_ids=None):
    """Existing byte-owner revocation; no events, provider work or body archive."""
    domain = hass.data.get(DOMAIN, {})
    if session_id is None and entry_ids is None:
        domain["tts_audio_authority_revision"] = domain.get("tts_audio_authority_revision", 0) + 1
    sources = {**domain.get("tts_audio_sources", {}), **domain.get("tts_audio_source_watches", {})}
    for watch in tuple(sources.values()):
        if ((session_id is None or watch.session_id == session_id)
                and (entry_ids is None or watch.entry_id in entry_ids)):
            watch.withdraw()


def collect_private_speech_sources(hass, *, session_id):
    """Reuse an existing publication/lifecycle tick, never create a monitor."""
    for watch in tuple(hass.data.get(DOMAIN, {}).get("tts_audio_source_watches", {}).values()):
        if watch.session_id == session_id:
            try:
                watch()
            except Exception:
                pass  # The source already withdrew its callbacks and bytes.


@dataclass
class TtsAudioItem:
    """Temporary audio item served to the paired DJConnect device."""

    data: bytes
    content_type: str
    extension: str
    expires_at: float
    owner_profile_id: str | None = None
    admission: Any = None
    cache_key: tuple | None = None
    speaker_grants: dict = field(default_factory=dict)
    delivery_device_id: str | None = None


def _store(hass: HomeAssistant) -> dict[str, TtsAudioItem]:
    return hass.data.setdefault(DOMAIN, {}).setdefault("tts_audio", {})


def cleanup_tts_audio(hass: HomeAssistant, now: float | None = None) -> None:
    """Remove expired TTS audio items."""
    current_time = time.time() if now is None else now
    store = _store(hass)
    for token, item in list(store.items()):
        if item.expires_at <= current_time:
            store.pop(token, None)


def get_tts_audio(hass: HomeAssistant, token: str) -> tuple[int, TtsAudioItem | None]:
    """Return status code and audio bytes for a temporary TTS token."""
    store = _store(hass)
    item = store.get(token)
    if item is None or item.owner_profile_id is not None:
        return 404, None
    if item.expires_at <= time.time():
        store.pop(token, None)
        return 410, None
    manager = hass.data.get(DOMAIN, {}).get('session_runtime_manager')
    if item.admission is None and getattr(manager, '_settings_repository', None) is not None:
        # Pre-upgrade anonymous slots carry no owner evidence. They cannot be
        # promoted to the connected settings protocol or a new playback grant.
        store.pop(token, None)
        return 404, None
    if item.admission is not None:
        try:
            item.admission()
        except Exception:
            store.pop(token, None)
            return 404, None
    return 200, item


def get_private_tts_audio(hass, token, owner_profile_id):
    """The caller must separately prove current ordinary paired Profile authority."""
    cleanup_tts_audio(hass)
    item = _store(hass).get(token)
    if item is None or item.owner_profile_id != owner_profile_id or item.admission is None:
        raise PermissionError("speech_audio_unavailable")
    from .speech_feedback import SpeechProviderChanged
    try:
        item.admission()
    except SpeechProviderChanged:
        _store(hass).pop(token, None)
        raise
    except Exception:
        _store(hass).pop(token, None)
        raise PermissionError("speech_audio_unavailable") from None
    return item


def grant_speaker_media(hass, asset_id, owner, guard):
    """Short media-fetch capability in the existing byte owner; never a legacy URL."""
    item = get_private_tts_audio(hass, asset_id, owner)
    guard()
    now = time.time()
    monotonic = time.monotonic()
    item.speaker_grants = {key: value for key, value in item.speaker_grants.items()
                           if value['expires_at'] > now and value['deadline'] > monotonic and value['reads'] < 4}
    if len(item.speaker_grants) >= 4:
        raise ValueError('speech_capacity')
    token = secrets.token_urlsafe(32)
    item.speaker_grants[token] = {'expires_at': min(item.expires_at, now + 30),
                                  'deadline': monotonic + 30, 'reads': 0, 'guard': guard}
    return token


def get_speaker_media(hass, asset_id, grant):
    """Revalidate original source, settings, pairing and exact HA target per fetch."""
    item = _store(hass).get(asset_id)
    if item is None or item.owner_profile_id is None:
        return None
    admitted = item.speaker_grants.get(grant)
    if admitted is None:
        return None
    try:
        if (admitted['expires_at'] <= time.time() or admitted['deadline'] <= time.monotonic()
                or admitted['reads'] >= 4):
            raise PermissionError('speech_media_expired')
        get_private_tts_audio(hass, asset_id, item.owner_profile_id)
        admitted['guard']()
    except Exception:
        item.speaker_grants.pop(grant, None)
        return None
    admitted['reads'] += 1
    return item


def store_private_tts_audio(hass, audio, *, owner_profile_id, admission, cache_key, expires_at):
    """Same RAM byte owner as legacy ESP; private slots have a hard total bound."""
    cleanup_tts_audio(hass)
    admission()
    store = _store(hass)
    private = [(key, value) for key, value in store.items() if value.owner_profile_id is not None]
    own = [(key, value) for key, value in private if value.owner_profile_id == owner_profile_id]
    if len(private) >= 64 or len(own) >= 8:
        raise ValueError("speech_capacity")
    if not 0 < len(audio.data) <= 2 * 1024 * 1024 or expires_at <= time.time():
        raise ValueError("unsupported_audio_extent")
    token = secrets.token_urlsafe(24)
    store[token] = TtsAudioItem(audio.data, audio.content_type, audio.extension, expires_at,
                              owner_profile_id, admission, cache_key)
    admission.on_withdraw(lambda: store.pop(token, None))
    return token


def store_tts_audio(
    hass: HomeAssistant,
    data: bytes,
    ttl_seconds: int = DEFAULT_DJ_RESPONSE_TTL_SECONDS,
    content_type: str = "audio/wav",
    extension: str = "wav",
    admission=None,
) -> str:
    """Store playable audio bytes temporarily and return a random download token."""
    cleanup_tts_audio(hass)
    token = secrets.token_urlsafe(24)
    _store(hass)[token] = TtsAudioItem(
        data=data,
        content_type=content_type,
        extension=extension,
        expires_at=time.time() + max(1, int(ttl_seconds)),
        admission=admission,
    )
    return token


async def async_create_dj_audio_url(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> str | None:
    """Create a temporary absolute audio URL for the ESP, if HA TTS can produce it."""
    conf = runtime.config
    admission = None
    try:
        from .announcement_policy import capture_announcement_admission
        admission = await capture_announcement_admission(hass, runtime)
        if admission is not None:
            from .ask_dj.dialogue import current_turn
            if current_turn.get() is not None:
                # Accepted private dialogue uses its reference/paired byte path,
                # never an anonymous legacy ESP URL or pre-commit synthesis.
                return None
            admission.guard()
            if admission.settings.announcement_output == 'text_only':
                return None
            from .speech_processor import configured_processor, synthesize
            selected = admission.settings.voice
            entity, voice = configured_processor(hass, conf, admission.locale,
                admission.settings.gender.value,
                selected_voice=selected.voice_id if selected.kind == 'provider_voice' else None)
            if selected.kind == 'provider_voice' and selected.provider_id != voice['engine']:
                return None
            state_guard = admission.guard
            def guard():
                state_guard()
                current_entity, current_voice = configured_processor(hass, runtime.config, admission.locale,
                    admission.settings.gender.value,
                    selected_voice=selected.voice_id if selected.kind == 'provider_voice' else None)
                if current_entity is not entity or current_voice != voice:
                    raise PermissionError('announcement_provider_changed')
            audio = await synthesize(entity, voice, text)
            guard()
        else:
            if not conf.get(CONF_DJ_RESPONSE_ENABLED, DEFAULT_DJ_RESPONSE_ENABLED):
                return None
            guard = None
            audio = await create_tts_audio(hass, text, conf)
    except UnsupportedTtsAudioError as exc:
        _LOGGER.debug(
            "DJConnect DJ response audio skipped; HA TTS returned unsupported ESP audio: %s",
            exc,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("DJConnect could not generate DJ response TTS: %s", exc)
        return None
    if not _is_supported_audio(audio):
        _LOGGER.warning("DJConnect TTS provider did not return supported WAV/MP3 audio")
        return None
    ttl = int(conf.get(CONF_DJ_RESPONSE_TTL_SECONDS, DEFAULT_DJ_RESPONSE_TTL_SECONDS))
    token = store_tts_audio(
        hass,
        audio.data,
        ttl,
        content_type=audio.content_type,
        extension=audio.extension,
        admission=guard,
    )
    base_url = await _async_ha_base_url(hass, conf)
    if guard is not None:
        try:
            guard()
        except Exception:
            _store(hass).pop(token, None)
            return None
    if not base_url:
        _store(hass).pop(token, None)
        _LOGGER.warning("DJConnect cannot build HA URL for DJ response audio")
        return None
    return f"{base_url.rstrip('/')}{API_TTS_BASE}/{token}.{audio.extension}"


async def async_send_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    """Post DJ response text and optional WAV URL to the DJConnect device."""
    payload = {"text": text}
    from .announcement_policy import capture_announcement_admission
    admission = await capture_announcement_admission(hass, runtime)
    if admission is not None:
        from .announcements import async_apply_announcement_output
        routed = await async_apply_announcement_output(hass, runtime, {'text': text},
            payload={}, generate_audio=True)
        audio_url = routed.get('audio_url')
    else:
        audio_url = await async_create_dj_audio_url(hass, runtime, text)
    if audio_url:
        payload["audio_url"] = audio_url

    local_url = await runtime.async_device_local_url(hass)
    if not local_url:
        raise RuntimeError("DJConnect device local_url is unknown")
    if admission is not None:
        try:
            admission.guard()
        except PermissionError:
            audio_url = None
            payload.pop('audio_url', None)
    url = local_url.rstrip("/") + "/api/device/dj_response"
    session = async_get_clientsession(hass)
    async with session.post(
        url,
        json=payload,
        headers=runtime.device_headers(),
        timeout=ClientTimeout(total=30),
    ) as resp:
        response_text = await resp.text()
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"ESP DJ response failed HTTP {resp.status}: {response_text}")
        try:
            data = await resp.json()
        except Exception:  # noqa: BLE001
            data = {"success": True, "message": response_text}

    result = {
        "success": bool(data.get("success", True)),
        "spoken": bool(data.get("spoken", False)),
        "displayed": bool(data.get("displayed", False)),
        "message": data.get("message"),
        "audio_url": bool(audio_url),
        "audio_url_value": audio_url,
        "audio_type": audio_url.rsplit(".", 1)[-1].lower() if audio_url else None,
    }
    runtime.update(
        last_dj_text=text,
        last_dj_spoken=result["spoken"],
        last_dj_displayed=result["displayed"],
        last_dj_response_at=time.time(),
        last_error=None,
    )
    _LOGGER.debug(
        "DJConnect DJ response result success=%s spoken=%s displayed=%s audio_url=%s audio_type=%s",
        result["success"],
        result["spoken"],
        result["displayed"],
        result["audio_url"],
        result["audio_type"],
    )
    return result


async def async_send_dj_response_best_effort(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    """Send DJ response without failing the voice command on TTS/device errors."""
    try:
        return await async_send_dj_response(hass, runtime, text)
    except Exception as exc:  # noqa: BLE001
        error = _format_exception(exc)
        runtime.update(last_error=error)
        _LOGGER.warning("DJConnect DJ response delivery failed: %s", error)
        return {
            "success": False,
            "spoken": False,
            "displayed": False,
            "message": error,
        }


def _is_supported_audio(audio: TtsAudio) -> bool:
    return audio.extension in {"wav", "mp3"} and bool(audio.data)


def _format_exception(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return type(exc).__name__


async def _async_ha_base_url(hass: HomeAssistant, conf: dict[str, Any]) -> str:
    return await async_ha_local_url(hass, conf)


async def prepare_private_tts_audio(hass, *, owner_profile_id, cache_key, expires_at, admission, synthesize):
    """Deduplicate only private presentation work; never dispatch original semantics."""
    import asyncio

    cleanup_tts_audio(hass)
    admission()
    for token, item in list(_store(hass).items()):
        if item.owner_profile_id == owner_profile_id and item.cache_key == cache_key:
            try:
                item.admission()
            except Exception:
                _store(hass).pop(token, None)
            else:
                return token
    domain = hass.data.setdefault(DOMAIN, {})
    pending = domain.setdefault("tts_audio_preparations", {})
    backoff = domain.setdefault("tts_audio_backoff", {})
    now = time.monotonic()
    for key, deadline in list(backoff.items()):
        if deadline <= now:
            del backoff[key]
    if cache_key in backoff:
        raise ValueError("speech_retry_backoff")
    job = pending.get(cache_key)
    if job is None:
        if len(pending) >= 64 or sum(key[0] == owner_profile_id for key in pending) >= 2:
            raise ValueError("speech_capacity")
        job = {"waiters": {}}
        def accepted_admission():
            for validate in list(job["waiters"].values()):
                try:
                    validate()
                except Exception:
                    continue
                return validate
            raise PermissionError("speech_request_withdrawn")

        async def prepare():
            try:
                async with asyncio.timeout(20):
                    accepted_admission()
                    audio = await synthesize()
                    validate = accepted_admission()
                    token = store_private_tts_audio(hass, audio, owner_profile_id=owner_profile_id,
                        admission=validate, cache_key=cache_key, expires_at=expires_at)
                    observed = getattr(validate, "on_synthesized", None)
                    if callable(observed):
                        observed()
                    return token
            except asyncio.CancelledError:
                raise
            except Exception:
                if len(backoff) >= 64:
                    backoff.pop(next(iter(backoff)))
                backoff[cache_key] = time.monotonic() + 60
                raise

        task = asyncio.create_task(prepare())
        job["task"] = task
        pending[cache_key] = job
        def finished(done):
            if pending.get(cache_key) is job:
                pending.pop(cache_key, None)
            if not done.cancelled():
                done.exception()  # An abandoned owner task never emits unobserved errors.
        task.add_done_callback(finished)
    if len(job["waiters"]) >= 8:
        raise ValueError("speech_capacity")
    caller = object()
    job["waiters"][caller] = admission
    def withdraw():
        job["waiters"].pop(caller, None)
        # Revocation/expiry/cancel stops orphan work, while a valid joined
        # caller retains the same actual owner task/slot until it is settled.
        if not job["waiters"] and not job["task"].done():
            job["task"].cancel()
    try:
        unsubscribe = admission.on_withdraw(withdraw)
    except BaseException:
        withdraw()
        raise
    try:
        try:
            token = await asyncio.shield(job["task"])
        except asyncio.CancelledError:
            # Source withdrawal cancels the owner job, not the HTTP caller.
            # Preserve genuine caller cancellation; otherwise return a typed
            # unavailable reference through the common preparation handler.
            if job["task"].cancelled() and not asyncio.current_task().cancelling():
                raise PermissionError("speech_source_withdrawn") from None
            raise
        admission()
        return token
    finally:
        if callable(unsubscribe):
            unsubscribe()
        withdraw()
