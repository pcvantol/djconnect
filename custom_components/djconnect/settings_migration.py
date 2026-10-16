"""Bounded owner-only legacy assessment; never infer new settings from old tone."""

from __future__ import annotations

from dataclasses import replace

from .domain.profile import ResponseStyle, VoiceStyle

TONES = frozenset({'classic_radio', 'late_night', 'energy', 'clean_host'})
RETIRED_ENTRY_KEYS = frozenset({'voice_profile', 'stt_engine', 'tts_engine', 'tts_voice',
                                'dj_response_prompt_preset', 'dj_response_prompt', 'dj_announcement_output'})


def _bound_entries(hass, household, owner):
    """Inspect configured real entries, not caller IDs or a global fallback Profile."""
    entries_api = getattr(hass.config_entries, 'async_entries', None)
    if callable(entries_api):
        entries = entries_api('djconnect')
    else:  # Small HA boundary fixtures; production always has the entries API.
        entries = [getattr(runtime, 'entry', None)
                   for runtime in list(hass.data.get('djconnect', {}).values())]
    seen = set()
    for entry in entries:
        if entry is None or entry.entry_id in seen:
            continue
        seen.add(entry.entry_id)
        config = {**entry.data, **entry.options}
        device = household.devices.get(config.get('device_id'))
        if device is not None and device.linked_profile_id == owner:
            yield entry, config


def assessment(hass, household, profile, *, activated, accepted_contract_version=None):
    """Only known enums and a bounded numeric value; no name/secret/prompt export."""
    if activated and accepted_contract_version in (None, 3):
        return {'version': 1, 'state': 'accepted_shared_settings', 'requires_review': False,
                'legacy_cleanup_pending': profile.metadata.dj_settings_version != 2 or any(
                    RETIRED_ENTRY_KEYS & config.keys() for _, config in _bound_entries(hass, household, profile.profile_id))}
    candidates = []
    if accepted_contract_version == 2:
        candidates.append({'field': 'settings_contract', 'value': 2,
                           'basis': 'explicit_six_field_review_required'})
    if profile.preferences.response_style != ResponseStyle.BALANCED:
        candidates.append({'field': 'response_style', 'value': profile.preferences.response_style.value,
                           'basis': 'legacy_profile_tone_not_persona'})
    if profile.preferences.voice_style != VoiceStyle.DEFAULT:
        candidates.append({'field': 'voice_style', 'value': profile.preferences.voice_style.value,
                           'basis': 'legacy_profile_tone_not_persona'})
    if type(profile.mood.value) is int and 0 <= profile.mood.value <= 100:
        candidates.append({'field': 'numeric_mood', 'value': profile.mood.value,
                           'basis': 'legacy_state_user_choice_provenance_unknown'})
    tones = sorted({config['voice_profile'] for _, config in _bound_entries(hass, household, profile.profile_id)
                    if type(config.get('voice_profile')) is str and config['voice_profile'] in TONES})
    candidates.extend({'field': 'voice_profile', 'value': tone,
                       'basis': 'legacy_bound_entry_tone_not_persona'} for tone in tones)
    from .domain.profile.dj_settings import ANNOUNCEMENT_OUTPUTS
    outputs = sorted({config['dj_announcement_output'] for _, config in _bound_entries(hass, household, profile.profile_id)
                      if type(config.get('dj_announcement_output')) is str
                      and config['dj_announcement_output'] in ANNOUNCEMENT_OUTPUTS})
    candidates.extend({'field': 'announcement_output', 'value': output,
                       'basis': 'legacy_entry_choice_provenance_unknown'} for output in outputs)
    return {'version': 1, 'state': 'choice_required' if candidates else 'no_legacy_choice_evidence',
            'requires_review': bool(candidates), 'complete_selection_fields':
            ['persona', 'voice', 'gender', 'mood', 'presence', 'announcement_output'] if candidates else [],
            'candidates': candidates, 'conflicting_entry_tones': len(tones) > 1,
            'automatic_persona_mapping': False}


async def async_retire_activated(hass, storage, repository):
    """Retryable cleanup after SQL acceptance, under existing owner locks.

    The marker is bookkeeping, never authority for a new settings value. Failed
    cleanup leaves the accepted SQL intent intact. No new worker/monitor.
    """
    household = await storage.async_load()
    defaults = await repository.async_export_defaults(tuple(household.profiles),
                                                       authorize=lambda: storage.household == household)
    expected_household = household
    for owner in defaults:
        if defaults[owner]['accepted_contract_version'] != 3:
            continue  # An old five-field receipt cannot retire output evidence.
        if storage.household != expected_household:
            return  # Another owner mutation won; retry from a new snapshot.
        profile = storage.household.profiles.get(owner)
        if profile is None:
            continue
        if profile.metadata.dj_settings_version != 2:
            retired = replace(profile,
                preferences=replace(profile.preferences, response_style=ResponseStyle.BALANCED,
                                    voice_style=VoiceStyle.DEFAULT),
                metadata=replace(profile.metadata, dj_settings_version=2))
            await storage.async_save(replace(expected_household,
                profiles={**expected_household.profiles, owner: retired}))
            expected_household = storage.household
        for entry, _ in _bound_entries(hass, storage.household, owner):
            data = {key: value for key, value in entry.data.items() if key not in RETIRED_ENTRY_KEYS}
            options = {key: value for key, value in entry.options.items() if key not in RETIRED_ENTRY_KEYS}
            if data != entry.data or options != entry.options:
                hass.config_entries.async_update_entry(entry, data=data, options=options)
