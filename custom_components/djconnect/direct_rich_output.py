"""Compiled closed output predicates for Direct rich v1.

Static schema-derived source; no JSON Schema loader/dependency on the hot path.
Field relations, original clocks, image admission and permissions remain separate.
"""
from datetime import datetime
import re

SCHEMA_SHA256 = '797fadc673d2803ff4460b7a57e8539f06d74287f194f462318eba713c80b404'


def _equal(left, right):
    return type(left) is type(right) and left == right


def _date(value):
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False

def _v1(v):
    return (type(v) is int
        and _equal(v, 1))


def _v2(v):
    return (type(v) is str
        and len(v) <= 36
        and re.fullmatch('^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$', v) is not None)


def _v3(v):
    return (type(v) is str
        and len(v) <= 128
        and re.fullmatch('^[A-Za-z0-9_-]{1,128}$', v) is not None)


def _v4(v):
    return (type(v) is int
        and v >= 0
        and v <= 9007199254740991)


def _v5(v):
    return (type(v) is str
        and len(v) <= 64
        and re.fullmatch('^[a-f0-9]{64}$', v) is not None)


def _v6(v):
    return (any(_equal(v, x) for x in ['active', 'stale']))


def _v7(v):
    return (any(_equal(v, x) for x in ['playing', 'paused', 'stopped', 'unknown']))


def _v9(v):
    return (any(_equal(v, x) for x in [None, 'chill', 'groove', 'energy', 'party']))


def _v8(v):
    return (type(v) is dict
        and {'value', 'revision'} <= v.keys()
        and v.keys() <= {'value', 'revision'}
        and _v9(v['value'])
        and _v4(v['revision']))


def _v10(v):
    return (any(_equal(v, x) for x in ['music_only', 'occasional', 'balanced', 'presenter']))


def _v11(v):
    return (any(_equal(v, x) for x in ['home_dj', 'radio_dj', 'club_dj', 'festival_dj']))


def _v13(v):
    return (v is None)


def _v16(v):
    return (type(v) is str
        and len(v) <= 64
        and _date(v))


def _v17(v):
    return (type(v) is str
        and len(v) <= 640
        and len(v.encode("utf-8", errors="strict")) <= 2560)


def _v19(v):
    return (type(v) is str
        and len(v) <= 512)


def _v20(v):
    return (type(v) is str
        and len(v) <= 2048)


def _v18(v):
    return (type(v) is dict
        and {'provider', 'url', 'license'} <= v.keys()
        and v.keys() <= {'provider', 'url', 'license'}
        and _v19(v['provider'])
        and _v20(v['url'])
        and _v19(v['license']))


def _v21(v):
    return (_equal(v, 'cc0_facts_authored_expression'))


def _v23(v):
    return (_equal(v, True))


def _v24(v):
    return (_equal(v, False))


def _v22(v):
    return (type(v) is dict
        and {'watch_replication', 'external_relay', 'passive_cache', 'os_snapshot'} <= v.keys()
        and v.keys() <= {'watch_replication', 'external_relay', 'passive_cache', 'os_snapshot'}
        and _v23(v['passive_cache'])
        and _v23(v['os_snapshot'])
        and _v24(v['external_relay'])
        and _v24(v['watch_replication']))


def _v15(v):
    return (type(v) is dict
        and {'source_attribution', 'moment_id', 'expires_at', 'rights', 'persona', 'published_at', 'text', 'usage_basis'} <= v.keys()
        and v.keys() <= {'moment_id', 'source_attribution', 'expires_at', 'rights', 'persona', 'published_at', 'text', 'usage_basis'}
        and _v3(v['moment_id'])
        and _v16(v['published_at'])
        and _v17(v['text'])
        and _v11(v['persona'])
        and _v18(v['source_attribution'])
        and _v21(v['usage_basis'])
        and _v16(v['expires_at'])
        and _v22(v['rights']))


def _v26(v):
    return (type(v) is dict
        and {'provider', 'revision_url', 'url', 'license'} <= v.keys()
        and v.keys() <= {'provider', 'revision_url', 'url', 'license'}
        and _v19(v['provider'])
        and _v20(v['url'])
        and _v19(v['license'])
        and _v20(v['revision_url']))


def _v27(v):
    return (_equal(v, 'public_artist_narration_v1'))


def _v30(v):
    return (_equal(v, 'source'))


def _v31(v):
    return (any(_equal(v, x) for x in ['en', 'nl', 'de', 'fr', 'es']))


def _v32(v):
    return (_equal(v, 'fetched_public_music_reference'))


def _v29(v):
    return (type(v) is dict
        and {'language', 'expires_at', 'license', 'content_hash', 'wikidata_id', 'revision_url', 'claim_scope', 'fetched_at', 'url', 'title', 'provider', 'kind'} <= v.keys()
        and v.keys() <= {'language', 'expires_at', 'license', 'content_hash', 'wikidata_id', 'kind', 'revision_url', 'claim_scope', 'fetched_at', 'url', 'provider', 'title'}
        and _v20(v['provider'])
        and _v20(v['title'])
        and _v20(v['url'])
        and _v30(v['kind'])
        and _v31(v['language'])
        and _v20(v['fetched_at'])
        and _v20(v['expires_at'])
        and _v20(v['license'])
        and _v20(v['revision_url'])
        and _v20(v['wikidata_id'])
        and _v5(v['content_hash'])
        and _v32(v['claim_scope']))


def _v28(v):
    return (type(v) is list
        and len(v) >= 1
        and len(v) <= 3
        and all(_v29(x) for x in v))


def _v34(v):
    return (_equal(v, 'CC-BY-SA-4.0'))


def _v35(v):
    return (_equal(v, 'https://creativecommons.org/licenses/by-sa/4.0/'))


def _v33(v):
    return (type(v) is dict
        and {'id', 'attribution_required', 'adapted', 'url'} <= v.keys()
        and v.keys() <= {'id', 'attribution_required', 'adapted', 'url'}
        and _v34(v['id'])
        and _v35(v['url'])
        and _v23(v['adapted'])
        and _v23(v['attribution_required']))


def _v25(v):
    return (type(v) is dict
        and {'sources', 'source_attribution', 'moment_id', 'expires_at', 'rights', 'persona', 'published_at', 'expression_license', 'text', 'usage_basis'} <= v.keys()
        and v.keys() <= {'sources', 'moment_id', 'source_attribution', 'expires_at', 'rights', 'persona', 'published_at', 'expression_license', 'text', 'usage_basis'}
        and _v3(v['moment_id'])
        and _v16(v['published_at'])
        and _v17(v['text'])
        and _v11(v['persona'])
        and _v26(v['source_attribution'])
        and _v27(v['usage_basis'])
        and _v16(v['expires_at'])
        and _v22(v['rights'])
        and _v28(v['sources'])
        and _v33(v['expression_license']))


def _v37(v):
    return (type(v) is dict
        and set() <= v.keys()
        and v.keys() <= set())


def _v38(v):
    return (_equal(v, 'runtime_authored_direction'))


def _v36(v):
    return (type(v) is dict
        and {'source_attribution', 'moment_id', 'expires_at', 'rights', 'persona', 'published_at', 'text', 'usage_basis'} <= v.keys()
        and v.keys() <= {'moment_id', 'source_attribution', 'expires_at', 'rights', 'persona', 'published_at', 'text', 'usage_basis'}
        and _v3(v['moment_id'])
        and _v16(v['published_at'])
        and _v17(v['text'])
        and _v11(v['persona'])
        and _v37(v['source_attribution'])
        and _v38(v['usage_basis'])
        and _v16(v['expires_at'])
        and _v22(v['rights']))


def _v14(v):
    return (sum((_v15(v), _v25(v), _v36(v),)) == 1)


def _v12(v):
    return (any((_v13(v), _v14(v),)))


def _v41(v):
    return (type(v) is str
        and len(v) <= 24
        and re.fullmatch('^[a-f0-9]{24}$', v) is not None)


def _v42(v):
    return (type(v) is str
        and len(v) <= 64
        and re.fullmatch('^spotify:track:[A-Za-z0-9]{22}$', v) is not None)


def _v44(v):
    return (_equal(v, 'Spotify'))


def _v45(v):
    return (_equal(v, 'spotify'))


def _v43(v):
    return (type(v) is dict
        and {'provider', 'url', 'mark'} <= v.keys()
        and v.keys() <= {'provider', 'url', 'mark'}
        and _v44(v['provider'])
        and _v45(v['mark'])
        and _v20(v['url']))


def _v46(v):
    return (_equal(v, 'spotify_temporary_passive_metadata'))


def _v40(v):
    return (type(v) is dict
        and {'source_url', 'observed_at', 'expires_at', 'subject_uri', 'attribution', 'track', 'album', 'artist', 'item_id', 'usage_basis'} <= v.keys()
        and v.keys() <= {'source_url', 'observed_at', 'expires_at', 'subject_uri', 'attribution', 'track', 'album', 'artist', 'item_id', 'usage_basis'}
        and _v41(v['item_id'])
        and _v42(v['subject_uri'])
        and _v19(v['track'])
        and _v19(v['artist'])
        and _v19(v['album'])
        and _v16(v['observed_at'])
        and _v16(v['expires_at'])
        and _v20(v['source_url'])
        and _v43(v['attribution'])
        and _v46(v['usage_basis']))


def _v39(v):
    return (any((_v13(v), _v40(v),)))


def _v49(v):
    return (any(_equal(v, x) for x in ['contribution', 'now_playing']))


def _v50(v):
    return (type(v) is str
        and len(v) <= 32
        and re.fullmatch('^[A-Za-z0-9_-]{32}$', v) is not None)


def _v52(v):
    return (type(v) is str
        and len(v) <= 64
        and re.fullmatch('^spotify:(track|album):[A-Za-z0-9]{22}$', v) is not None)


def _v53(v):
    return (any(_equal(v, x) for x in ['track', 'album']))


def _v54(v):
    return (type(v) is str
        and len(v) <= 64
        and re.fullmatch('^spotify:album:[A-Za-z0-9]{22}$', v) is not None)


def _v51(v):
    return (type(v) is dict
        and {'provider', 'uri', 'type'} <= v.keys()
        and v.keys() <= {'provider', 'uri', 'type', 'album_uri'}
        and _v45(v['provider'])
        and _v52(v['uri'])
        and _v53(v['type'])
        and ('album_uri' not in v or _v54(v['album_uri'])))


def _v55(v):
    return (any(_equal(v, x) for x in ['contextual_cover', 'current_cover']))


def _v56(v):
    return (type(v) is dict
        and {'es', 'de', 'fr', 'nl', 'en'} <= v.keys()
        and v.keys() <= {'es', 'nl', 'en', 'de', 'fr'}
        and _v19(v['en'])
        and _v19(v['nl'])
        and _v19(v['de'])
        and _v19(v['fr'])
        and _v19(v['es']))


def _v57(v):
    return (type(v) is int
        and v >= 1
        and v <= 4096)


def _v58(v):
    return (_equal(v, 'spotify_temporary_passive_cover'))


def _v59(v):
    return (type(v) is int
        and v >= 1
        and v <= 256000)


def _v60(v):
    return (any(_equal(v, x) for x in ['image/png', 'image/jpeg']))


def _v48(v):
    return (type(v) is dict
        and {'captured_at', 'source_url', 'expires_at', 'asset_id', 'subject', 'height', 'rights', 'slot', 'attribution', 'mime_type', 'bytes_sha256', 'crop_allowed', 'byte_length', 'width', 'media_revision', 'role', 'usage_basis', 'alt_text'} <= v.keys()
        and v.keys() <= {'source_url', 'subject', 'height', 'bytes_sha256', 'byte_length', 'width', 'media_revision', 'slot', 'role', 'usage_basis', 'captured_at', 'expires_at', 'asset_id', 'rights', 'attribution', 'crop_allowed', 'mime_type', 'alt_text'}
        and _v49(v['slot'])
        and _v50(v['asset_id'])
        and _v51(v['subject'])
        and _v55(v['role'])
        and _v41(v['media_revision'])
        and _v16(v['captured_at'])
        and _v16(v['expires_at'])
        and _v20(v['source_url'])
        and _v43(v['attribution'])
        and _v56(v['alt_text'])
        and _v57(v['width'])
        and _v57(v['height'])
        and _v24(v['crop_allowed'])
        and _v58(v['usage_basis'])
        and _v22(v['rights'])
        and _v5(v['bytes_sha256'])
        and _v59(v['byte_length'])
        and _v60(v['mime_type'])
        and v["width"] * v["height"] <= 16000000)


def _v47(v):
    return (type(v) is list
        and len(v) <= 2
        and all(_v48(x) for x in v))


def _v63(v):
    return (_equal(v, 'available'))


def _v64(v):
    return (_equal(v, 'qualified'))


def _v62(v):
    return (type(v) is dict
        and {'state', 'reason'} <= v.keys()
        and v.keys() <= {'state', 'reason'}
        and _v63(v['state'])
        and _v64(v['reason']))


def _v66(v):
    return (_equal(v, 'suppressed'))


def _v67(v):
    return (any(_equal(v, x) for x in ['presence_music_only', 'intentional_silence']))


def _v65(v):
    return (type(v) is dict
        and {'state', 'reason'} <= v.keys()
        and v.keys() <= {'state', 'reason'}
        and _v66(v['state'])
        and _v67(v['reason']))


def _v69(v):
    return (_equal(v, 'stale'))


def _v70(v):
    return (_equal(v, 'original_snapshot_expired'))


def _v68(v):
    return (type(v) is dict
        and {'state', 'reason'} <= v.keys()
        and v.keys() <= {'state', 'reason'}
        and _v69(v['state'])
        and _v70(v['reason']))


def _v72(v):
    return (_equal(v, 'unavailable'))


def _v73(v):
    return (any(_equal(v, x) for x in ['source_not_qualified', 'original_deadline_expired', 'copy_too_long', 'representation_not_supported', 'no_publication', 'no_observation', 'subject_changed', 'playback_inactive', 'no_eligible_context', 'not_prepared', 'no_matching_subject', 'asset_not_supported']))


def _v71(v):
    return (type(v) is dict
        and {'state', 'reason'} <= v.keys()
        and v.keys() <= {'state', 'reason'}
        and _v72(v['state'])
        and _v73(v['reason']))


def _v61(v):
    return (sum((_v62(v), _v65(v), _v68(v), _v71(v),)) == 1)


def _v0(v):
    return (type(v) is dict
        and {'delivery_sequence', 'state', 'presence', 'observed_at_ms', 'generation', 'session_id', 'persona', 'expires_at_ms', 'mood', 'contribution', 'artwork_status', 'contribution_status', 'now_playing', 'playback_state', 'now_playing_status', 'binding_id', 'schema_version', 'frame_id', 'artwork'} <= v.keys()
        and v.keys() <= {'contribution_status', 'delivery_sequence', 'state', 'presence', 'now_playing', 'observed_at_ms', 'generation', 'session_id', 'now_playing_status', 'schema_version', 'binding_id', 'persona', 'expires_at_ms', 'frame_id', 'mood', 'artwork', 'contribution', 'artwork_status', 'playback_state'}
        and _v1(v['schema_version'])
        and _v2(v['binding_id'])
        and _v2(v['generation'])
        and _v3(v['session_id'])
        and _v4(v['delivery_sequence'])
        and _v5(v['frame_id'])
        and _v6(v['state'])
        and _v4(v['observed_at_ms'])
        and _v4(v['expires_at_ms'])
        and _v7(v['playback_state'])
        and _v8(v['mood'])
        and _v10(v['presence'])
        and _v11(v['persona'])
        and _v12(v['contribution'])
        and _v39(v['now_playing'])
        and _v47(v['artwork'])
        and _v61(v['contribution_status'])
        and _v61(v['now_playing_status'])
        and _v61(v['artwork_status']))


def _v75(v):
    return (_equal(v, 'djconnect-direct-rich-v1'))


def _v76(v):
    return (any(_equal(v, x) for x in ['widget', 'live_activity']))


def _v77(v):
    return (_equal(v, 'active'))


def _v78(v):
    return (type(v) is int
        and v >= 1
        and v <= 9007199254740991)


def _v79(v):
    return (_v0(v))


def _v80(v):
    return (type(v) is str
        and len(v) <= 55
        and re.fullmatch('^djcrichread_[A-Za-z0-9_-]{43}$', v) is not None)


def _v81(v):
    return (type(v) is str
        and len(v) <= 56
        and re.fullmatch('^djcrichasset_[A-Za-z0-9_-]{43}$', v) is not None)


def _v74(v):
    return (type(v) is dict
        and {'frame', 'asset_credential', 'read_credential', 'purpose_expires_at_ms', 'purpose_id', 'profile_id', 'success', 'state', 'purpose_issued_at_ms', 'surface', 'operation_id', 'contract_version', 'request_sha256'} <= v.keys()
        and v.keys() <= {'frame', 'asset_credential', 'read_credential', 'purpose_expires_at_ms', 'purpose_id', 'profile_id', 'success', 'state', 'purpose_issued_at_ms', 'surface', 'operation_id', 'contract_version', 'request_sha256'}
        and _v23(v['success'])
        and _v1(v['contract_version'])
        and _v75(v['profile_id'])
        and _v2(v['operation_id'])
        and _v2(v['purpose_id'])
        and _v76(v['surface'])
        and _v77(v['state'])
        and _v78(v['purpose_issued_at_ms'])
        and _v78(v['purpose_expires_at_ms'])
        and _v5(v['request_sha256'])
        and _v79(v['frame'])
        and _v80(v['read_credential'])
        and _v81(v['asset_credential']))


def _v82(v):
    return (type(v) is dict
        and {'frame', 'purpose_expires_at_ms', 'purpose_id', 'profile_id', 'success', 'state', 'purpose_issued_at_ms', 'surface', 'operation_id', 'contract_version', 'request_sha256'} <= v.keys()
        and v.keys() <= {'frame', 'purpose_expires_at_ms', 'purpose_id', 'profile_id', 'success', 'state', 'purpose_issued_at_ms', 'surface', 'operation_id', 'contract_version', 'request_sha256'}
        and _v23(v['success'])
        and _v1(v['contract_version'])
        and _v75(v['profile_id'])
        and _v2(v['operation_id'])
        and _v2(v['purpose_id'])
        and _v76(v['surface'])
        and _v77(v['state'])
        and _v78(v['purpose_issued_at_ms'])
        and _v78(v['purpose_expires_at_ms'])
        and _v5(v['request_sha256'])
        and _v79(v['frame']))


def _v84(v):
    return (any(_equal(v, x) for x in ['active', 'withdrawn', 'expired', 'unknown']))


def _v83(v):
    return (type(v) is dict
        and {'purpose_expires_at_ms', 'purpose_id', 'profile_id', 'success', 'state', 'purpose_issued_at_ms', 'surface', 'operation_id', 'contract_version'} <= v.keys()
        and v.keys() <= {'purpose_expires_at_ms', 'purpose_id', 'profile_id', 'success', 'state', 'purpose_issued_at_ms', 'surface', 'operation_id', 'contract_version'}
        and _v23(v['success'])
        and _v1(v['contract_version'])
        and _v75(v['profile_id'])
        and _v2(v['operation_id'])
        and _v2(v['purpose_id'])
        and _v76(v['surface'])
        and _v84(v['state'])
        and _v78(v['purpose_issued_at_ms'])
        and _v78(v['purpose_expires_at_ms']))


def _v86(v):
    return (any(_equal(v, x) for x in ['invalid_request', 'unauthorized', 'rich_not_allowed', 'rich_history_unknown', 'rich_asset_unavailable', 'rich_purpose_consumed', 'rich_frame_changed', 'rich_capacity', 'rich_unavailable', 'rich_frame_unavailable']))


def _v85(v):
    return (type(v) is dict
        and {'success', 'contract_version', 'error'} <= v.keys()
        and v.keys() <= {'success', 'contract_version', 'error'}
        and _v24(v['success'])
        and _v1(v['contract_version'])
        and _v86(v['error']))

VALIDATORS = {
    'frame': _v0,
    'authorize_response': _v74,
    'read_response': _v82,
    'manage_response': _v83,
    'error_response': _v85,
    'contribution': _v12,
    'now_playing': _v39,
    'artwork_item': _v48,
}

def _wire_bytes(value, key=""):
    if type(value) is str:
        maximum = 2560 if key == "text" else 2048 if key in {"url", "source_url", "revision_url"} else 512
        return len(value.encode("utf-8", errors="strict")) <= maximum
    if type(value) is dict:
        return all(_wire_bytes(v, k) for k, v in value.items())
    if type(value) is list:
        return all(_wire_bytes(v, key) for v in value)
    return True


def valid(kind, value):
    try:
        return _wire_bytes(value) and VALIDATORS[kind](value) is True
    except (KeyError, TypeError, ValueError, OverflowError, UnicodeError):
        return False
