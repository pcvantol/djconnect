"""Strict ordinary-paired owner read; no consumer intelligence or mutations."""
from __future__ import annotations

from .const import CLIENT_TYPES, DOMAIN
from .session_forecast import VERSION


async def async_handle_forecast(hass, data, *, headers=None):
    from .api_handlers import _async_owner_broadcast_session_context
    from .profile_context import profile_storage
    from .request_auth import authorize_runtime_device_request, request_token, resolve_runtime, runtime_matches_device

    def error(code, status):
        return {'success': False, 'error': code}, status

    fields = {'contract_version', 'client_type', 'device_id', 'session_id'}
    if not isinstance(data, dict) or set(data) != fields:
        return error('invalid_request', 400)
    if type(data['contract_version']) is not int or data['contract_version'] != VERSION:
        return error('unsupported_contract_version', 400)
    if any(type(data[k]) is not str or not data[k] for k in fields - {'contract_version'}):
        return error('invalid_request', 400)
    if data['client_type'] not in CLIENT_TYPES or data['client_type'] == 'windows':
        return error('invalid_client_type', 400)
    headers = headers or {}
    if not str(headers.get('Authorization', '')).startswith('Bearer '):
        return error('unauthorized', 401)
    runtime = resolve_runtime(hass, data['device_id'], headers)
    if runtime is None:
        return error('unauthorized', 401)
    entry = getattr(runtime, 'entry', None)
    entry_id = str(getattr(entry, 'entry_id', ''))
    generation = getattr(runtime, '_receiver_end_generation', 0)

    def paired():
        if (entry is None or hass.data.get(DOMAIN, {}).get(entry_id) is not runtime
                or hass.config_entries.async_get_entry(entry_id) is not entry
                or entry.disabled_by is not None
                or getattr(getattr(entry, 'state', None), 'value', None) != 'loaded'):
            return False
        conf = {**entry.data, **entry.options}
        known = getattr(runtime, 'device_status', {}).get('device_id') or getattr(runtime, 'pairing_device_id', '') or conf.get('device_id')
        return (conf.get('device_token') == request_token(headers)
                and conf.get('device_id') == known == data['device_id']
                and conf.get('client_type') == data['client_type']
                and headers.get('X-DJConnect-Device-ID', data['device_id']) == data['device_id']
                and getattr(runtime, '_receiver_end_generation', 0) == generation
                and runtime_matches_device(runtime, data['device_id'])
                and authorize_runtime_device_request(runtime, headers, data['device_id'], data['client_type']))

    if not paired():
        return error('unauthorized', 401)
    result, status, manager, profile_id = await _async_owner_broadcast_session_context(
        hass, data, headers=headers, source='session_forecast')
    if manager is None:
        return result, status
    storage = profile_storage(hass)
    try:
        profile = storage.resolver().resolve_bound_device(data['device_id'])
        preferences = profile.preferences
        backend_id, account_id = preferences.default_backend_id, preferences.default_music_account_id
        account = storage.household.music_accounts.get(account_id)
        backend = storage.household.music_backends.get(backend_id)
        source = manager._history_source_contexts.get(data['session_id'], {})
        if source.get('backend_id', backend_id) != backend_id or source.get('music_account_id', account_id) != account_id:
            return error('unauthorized', 401)
    except Exception:
        return error('unauthorized', 401)

    def owner_current():
        if (not paired() or hass.data.get(DOMAIN, {}).get('session_runtime_manager') is not manager
                or manager.receiver_entry_generation(entry_id) != generation):
            return False
        try:
            current = storage.resolver().resolve_bound_device(data['device_id'])
            return (current.profile_id == profile_id and current.state.value == 'active'
                    and current.preferences.default_backend_id == backend_id
                    and current.preferences.default_music_account_id == account_id
                    and (account is None or (account.state.value == 'active'
                         and source.get('provider_account_id', account.provider_account_id) == account.provider_account_id))
                    and storage.household.music_accounts.get(account_id) is account
                    and storage.household.music_backends.get(backend_id) is backend)
        except Exception:
            return False

    try:
        snapshot = await manager.async_forecast_snapshot(owner_profile_id=profile_id,
            session_id=data['session_id'], authorize=owner_current)
    except PermissionError:
        return error('unauthorized', 401)
    if snapshot is None:
        return error('active_session_not_found', 404)
    return {'success': True, 'contract_version': VERSION,
            'session_id': data['session_id'], 'forecast': snapshot}, 200
