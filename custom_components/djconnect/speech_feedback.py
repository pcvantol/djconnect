"""Private bounded provider observations and safe functional client notices."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime


class SpeechProviderChanged(PermissionError):
    """Only raised after the independent owner/source admission still succeeds."""
    def __init__(self, reason, locale="en"):
        super().__init__(reason)
        self.locale = locale


INSTRUCTION = {
    "en": "In Home Assistant, check the Assist pipeline selected in DJConnect: its TTS provider, language and voice. The text remains available.",
    "nl": "Controleer in Home Assistant de Assist-pipeline die je in DJConnect hebt gekozen: de TTS-provider, taal en stem. De tekst blijft beschikbaar.",
    "de": "Prüfe in Home Assistant die in DJConnect gewählte Assist-Pipeline: TTS-Anbieter, Sprache und Stimme. Der Text bleibt verfügbar.",
    "fr": "Dans Home Assistant, vérifiez le pipeline Assist choisi dans DJConnect : fournisseur TTS, langue et voix. Le texte reste disponible.",
    "es": "En Home Assistant, revisa el flujo de Assist elegido en DJConnect: proveedor TTS, idioma y voz. El texto sigue disponible.",
}
TITLES = {
    "tts_configuration_required": ("Speech is not configured", "Spraak is niet ingesteld", "Sprachausgabe ist nicht eingerichtet", "La synthèse vocale n’est pas configurée", "La voz no está configurada"),
    "tts_provider_unavailable": ("Speech provider unavailable", "Spraakprovider niet beschikbaar", "Sprachanbieter nicht verfügbar", "Fournisseur vocal indisponible", "Proveedor de voz no disponible"),
    "tts_voice_language_unavailable": ("Speech setting unavailable", "Spraakinstelling niet beschikbaar", "Spracheinstellung nicht verfügbar", "Paramètre vocal indisponible", "Configuración de voz no disponible"),
    "tts_preparation_failed": ("Speech could not be prepared", "Uitspreken is mislukt", "Sprachausgabe fehlgeschlagen", "La préparation vocale a échoué", "No se ha podido preparar la voz"),
    "tts_configuration_changed": ("Speech settings changed", "Spraakinstellingen gewijzigd", "Spracheinstellungen geändert", "Paramètres vocaux modifiés", "La configuración de voz ha cambiado"),
}


def notification(reason, locale="en", *, retry_after=0):
    """No exception text, provider payload, source text or arbitrary navigation."""
    code = ({"processor_not_qualified": "tts_configuration_required",
             "tts_provider_unavailable": "tts_provider_unavailable",
             "no_matching_locale": "tts_voice_language_unavailable",
             "no_matching_voice": "tts_voice_language_unavailable",
             "voice_gender_unavailable": "tts_voice_language_unavailable",
             "speech_configuration_changed": "tts_configuration_changed",
             "speech_preparation_failed": "tts_preparation_failed",
             "speech_preparation_timeout": "tts_preparation_failed",
             "unsupported_audio_extent": "tts_preparation_failed",
             "unsupported_audio_type": "tts_preparation_failed",
             "speech_retry_backoff": "tts_preparation_failed"}).get(reason)
    if code is None:
        return None
    family = str(locale or "en").replace("_", "-").split("-", 1)[0].lower()
    if family not in INSTRUCTION:
        family = "en"
    return {"schema_version": 1, "code": code, "message_key": "speech." + code,
            "severity": "warning", "presentation": "inline", "locale": family,
            "title": TITLES[code][list(INSTRUCTION).index(family)], "message": INSTRUCTION[family],
            "actions": ["review_ha_tts_configuration", "retry_speech_preparation"],
            "retryable": True, "retry_after_seconds": max(0, min(60, int(retry_after))),
            "preserve_text": True, "repeat_original_request": False}


def _identity(voice):
    return hashlib.sha256(json.dumps(voice, sort_keys=True).encode()).hexdigest()[:24]


def _owner_key(runtime, owner):
    return (getattr(getattr(runtime, "entry", None), "entry_id", ""), id(runtime), owner)


def record(hass, runtime, owner, voice, *, provider, reason=None):
    """One short observation per entry/Profile, max64; no accepted/source text."""
    rows = hass.data.setdefault("djconnect", {}).setdefault("speech_provider_observations", {})
    now = time.monotonic()
    for key, item in list(rows.items()):
        if item["deadline"] <= now:
            rows.pop(key, None)
    key = _owner_key(runtime, owner)
    if key not in rows and len(rows) >= 64:
        rows.pop(next(iter(rows)))
    rows[key] = {"identity": _identity(voice), "provider_incarnation": id(provider), "reason": reason,
                 "observed_at": datetime.now(UTC).isoformat(),
                 "deadline": now + 300, "retry_at": now + 60 if reason else now}


def status(hass, runtime, owner, options, locale):
    """Pure read; configuration availability is never a synthesis health check."""
    ready = options.get("state") == "available"
    voice = options.get("provider_voice")
    rows = hass.data.get("djconnect", {}).get("speech_provider_observations", {})
    observation = rows.get(_owner_key(runtime, owner))
    now = time.monotonic()
    if (not ready or voice is None or observation is None
            or observation["deadline"] <= now or observation["identity"] != _identity(voice)):
        observation = None
    if observation:
        from .speech_processor import configured_processor, ProcessorUnavailable
        try:
            provider, _ = configured_processor(hass, runtime.config,
                voice["locale"].replace("_", "-").split("-", 1)[0], "default")
        except ProcessorUnavailable:
            observation = None
        else:
            if id(provider) != observation["provider_incarnation"]:
                observation = None
    reason = options.get("reason") if not ready else observation["reason"] if observation else None
    retry = max(0, int(observation["retry_at"] - now + .999)) if observation else 0
    result = {"schema_version": 1, "configuration_state": "ready" if ready else "unavailable",
              "synthesis_state": ("failed" if observation["reason"] else "succeeded") if observation else "not_tested",
              "reason": reason, "observed_at": observation["observed_at"] if observation else None,
              "retry_after_seconds": retry, "cache_policy": "private,no-store"}
    result["notification"] = notification(reason, locale, retry_after=retry)
    result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:24]
    return result
