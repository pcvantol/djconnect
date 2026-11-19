from __future__ import annotations

import base64
import hashlib
import secrets
import re
from datetime import datetime, UTC
from typing import Any

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_SPOTIFY_CALLBACK, SPOTIFY_SCOPES

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyTokenRefreshError(RuntimeError):
    """Raised when Spotify rejects a refresh token."""

    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status = status
        self.body = body
        self.error = str(body.get("error") or "")
        self.error_description = str(body.get("error_description") or "")
        super().__init__(
            f"Spotify token refresh failed HTTP {status}: {self.error or 'unknown'}"
        )


def normalize_spotify_scopes(
    scopes: str | list[str] | tuple[str, ...] | None,
) -> list[str]:
    """Return unique Spotify scopes while preserving configured order."""
    if isinstance(scopes, str):
        values = scopes.split()
    elif scopes:
        values = [str(scope).strip() for scope in scopes]
    else:
        values = []
    seen: set[str] = set()
    normalized: list[str] = []
    for scope in values:
        if scope and scope not in seen:
            normalized.append(scope)
            seen.add(scope)
    return normalized


def missing_spotify_scopes(
    scopes: str | list[str] | tuple[str, ...] | None,
) -> list[str]:
    """Return DJConnect required scopes missing from a stored OAuth scope list."""
    existing = set(normalize_spotify_scopes(scopes))
    return [scope for scope in SPOTIFY_SCOPES if scope not in existing]


def ensure_spotify_scopes(
    scopes: str | list[str] | tuple[str, ...] | None,
) -> str:
    """Append any newly required DJConnect scopes to an OAuth scope string."""
    normalized = normalize_spotify_scopes(scopes)
    existing = set(normalized)
    for scope in SPOTIFY_SCOPES:
        if scope not in existing:
            normalized.append(scope)
            existing.add(scope)
    return " ".join(normalized)


SCOPE_EVIDENCE_KEY = "spotify_scope_evidence"
_SCOPE_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
_SCOPE_FIELDS = {'version', 'status', 'source', 'observed_at', 'client_id_sha256', 'granted_scopes'}


def _safe_scope_evidence(value, client_id):
    if (not isinstance(value, dict) or set(value) != _SCOPE_FIELDS
            or type(value.get('version')) is not int or value['version'] != 1
            or value.get('source') not in {'authorization_code', 'refresh_token'}
            or value.get('status') not in {'known', 'unknown'}
            or value.get('client_id_sha256') != hashlib.sha256(str(client_id).encode()).hexdigest()):
        return None
    try:
        stamp = datetime.fromisoformat(value['observed_at'])
        if stamp.tzinfo is None:
            return None
    except (TypeError, ValueError):
        return None
    scopes = value.get('granted_scopes')
    if value['status'] == 'known':
        if (not isinstance(scopes, list) or len(scopes) > 64
                or any(not isinstance(v, str) or not _SCOPE_NAME.fullmatch(v) for v in scopes)
                or len(set(scopes)) != len(scopes)):
            return None
    elif scopes is not None:
        return None
    return {**value, 'granted_scopes': list(scopes) if scopes is not None else None}


def spotify_scope_evidence(token, *, requested, client_id, source,
                           previous=None, observed_at=None):
    """Provider scope metadata only; requested never stands in for granted."""
    if source not in {'authorization_code', 'refresh_token'}:
        raise ValueError('invalid_scope_evidence_source')
    prior = _safe_scope_evidence(previous, client_id)
    raw = token.get('scope') if isinstance(token, dict) else None
    if source == 'refresh_token' and isinstance(token, dict) and 'scope' not in token and prior is not None:
        return prior
    scopes = raw.split() if isinstance(raw, str) and len(raw) <= 4096 else None
    known = (scopes is not None and len(scopes) <= 64
             and all(_SCOPE_NAME.fullmatch(scope) for scope in scopes))
    return {'version': 1, 'status': 'known' if known else 'unknown', 'source': source,
            'observed_at': observed_at or datetime.now(UTC).isoformat(),
            'client_id_sha256': hashlib.sha256(str(client_id).encode()).hexdigest(),
            'granted_scopes': list(dict.fromkeys(scopes)) if known else None}


def spotify_scope_status(config):
    """Safe separate diagnostics; this receipt never authorizes an API action."""
    requested = normalize_spotify_scopes(config.get('spotify_scopes'))
    evidence = _safe_scope_evidence(config.get(SCOPE_EVIDENCE_KEY), config.get('spotify_client_id', ''))
    granted = evidence['granted_scopes'] if evidence and evidence['status'] == 'known' else None
    return {'requested_scopes': requested, 'granted_scopes': granted,
            'granted_scope_status': 'known' if granted is not None else 'unknown',
            'granted_scope_evidence': evidence,
            'missing_requested_scopes': missing_spotify_scopes(requested),
            'missing_granted_scopes': missing_spotify_scopes(granted) if granted is not None else None}


def store_spotify_scope_evidence(hass, entry, token, *, client_id):
    """Ordinary refresh persistence through the same current credential owner."""
    entries = getattr(hass, 'config_entries', None)
    getter = getattr(entries, 'async_get_entry', None)
    updater = getattr(entries, 'async_update_entry', None)
    if (entry is None or not callable(getter) or not callable(updater)
            or getter(entry.entry_id) is not entry
            or getattr(entry, 'disabled_by', None) is not None
            or str({**entry.data, **getattr(entry, 'options', {})}.get('spotify_client_id', '')) != str(client_id)):
        return False
    evidence = spotify_scope_evidence(token, requested=entry.data.get('spotify_scopes'),
        client_id=client_id, source='refresh_token', previous=entry.data.get(SCOPE_EVIDENCE_KEY))
    if evidence != entry.data.get(SCOPE_EVIDENCE_KEY):
        updater(entry, data={**entry.data, SCOPE_EVIDENCE_KEY: evidence})
        return True
    return False


def create_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:96]


def create_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_redirect_uri(base_url: str) -> str:
    return base_url.rstrip("/") + API_SPOTIFY_CALLBACK


def build_authorize_url(client_id: str, redirect_uri: str, scopes: str, state: str, code_verifier: str) -> str:
    from urllib.parse import urlencode
    query = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "code_challenge_method": "S256",
        "code_challenge": create_code_challenge(code_verifier),
        "state": state,
        "scope": scopes,
    })
    return f"{SPOTIFY_AUTHORIZE_URL}?{query}"


async def exchange_code_for_refresh_token(
    hass: HomeAssistant,
    *,
    client_id: str,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    async with session.post(SPOTIFY_TOKEN_URL, data=data, timeout=ClientTimeout(total=20)) as resp:
        body = await resp.json(content_type=None)
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"Spotify token exchange failed HTTP {resp.status}: {body}")
        if not body.get("refresh_token"):
            raise RuntimeError("Spotify token response did not contain a refresh_token")
        return body


async def refresh_access_token(
    hass: HomeAssistant,
    *,
    client_id: str,
    refresh_token: str,
) -> dict[str, Any]:
    """Refresh a Spotify access token using HA-stored PKCE OAuth credentials."""
    session = async_get_clientsession(hass)
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    async with session.post(
        SPOTIFY_TOKEN_URL,
        data=data,
        timeout=ClientTimeout(total=12),
    ) as resp:
        body = await resp.json(content_type=None)
        if resp.status < 200 or resp.status >= 300:
            raise SpotifyTokenRefreshError(resp.status, body)
        return body
