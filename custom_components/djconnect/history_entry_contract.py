"""Representation negotiation after existing private-history authorization.

No source admission, retention, publication, new storage or substitute bodies.
"""
from contextvars import ContextVar

from .session_history_projection import HistoryQueryError

version_context = ContextVar('djconnect_history_entry_version', default=1)


class HistoryEntryUpgradeRequired(HistoryQueryError):
    """A valid private page has no lossless representation for the old decoder."""


def request_version(value=None):
    if value is None:
        return 1
    if type(value) is int and value in (1,2):
        return value
    if type(value) is str and value in ('1','2'):
        return int(value)
    raise HistoryQueryError('unsupported_history_contract_version')


def cursor_scope(scope):
    return {**scope,'history_contract_version':2} if version_context.get()==2 else scope


def upgrade_error():
    return {'success':False,'error':'history_contract_upgrade_required',
        'required_history_contract_version':2,'supported_history_contract_versions':[1,2]}


def represent(result, version):
    """Do not reinterpret, omit, relabel or partially accept source-derived rows."""
    if version == 1:
        entries = [*result.get('entries',[]),*result.get('matches',[])]
        if isinstance(result.get('entry'),dict):
            entries.append(result['entry'])
        for entry in entries:
            if (entry.get('kind') not in {'playback_observed','dj_moment','conversation_user','conversation_dj'}
                    or (entry.get('kind') == 'dj_moment' and entry.get('archive_basis') not in
                        {'cc0_normalized_fields_v1','runtime_authored_direction_v1'})):
                raise HistoryEntryUpgradeRequired('history_contract_upgrade_required')
        return result
    if version != 2:
        raise HistoryQueryError('unsupported_history_contract_version')
    return {**result,'schema_version':2,'history_contract_version':2}
