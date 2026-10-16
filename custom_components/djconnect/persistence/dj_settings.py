"""One durable acceptance for typed defaults, live intent, Mood and dedup proof."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import re

from ..domain.profile.dj_settings import DJSettings, SettingsValidationError
from ..transport_operations import (
    FUTURE_SKEW_MS, LIFETIME_MS, MAX_OWNER_RECORDS, MAX_RECORDS,
    OperationError, operation_created_ms,
)
from .service import PersistenceRepository


class SettingsCommitError(ValueError):
    """Closed failure code; application transport decides its authorized response."""


class SettingsRevisionConflict(SettingsCommitError):
    def __init__(self, current):
        super().__init__('settings_revision_conflict')
        self.current = current


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _identifier(value):
    if (type(value) is not str or not 0 < len(value) <= 128
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SettingsCommitError('invalid_settings_identity')
    return value


def _revision(value):
    if type(value) is not int or value < 0:
        raise SettingsCommitError('invalid_settings_revision')
    return value


@dataclass(frozen=True)
class SessionSettingsContext:
    session_id: str
    generation: str
    expected_revision: int
    effective: DJSettings

    def __post_init__(self):
        _identifier(self.session_id)
        _identifier(self.generation)
        _revision(self.expected_revision)
        if not isinstance(self.effective, DJSettings):
            raise SettingsValidationError('invalid_effective_settings')


class ProfileDJSettingsRepository(PersistenceRepository):
    """Existing Profile domain owner backed by the existing persistence service.

    Runtime owns admission and holds its lifecycle lock through this commit and
    projection. Authorization runs on the HA event loop before staging and at the final
    admission fence. SQL callbacks contain only immutable domain data.
    """

    @staticmethod
    def _defaults(tx, owner):
        row = tx.fetchone(
            'SELECT settings,revision,updated_at FROM djconnect_profile_dj_settings WHERE owner_profile_id=?',
            (owner,),
        )
        if row is None:
            return DJSettings(), 0, ''
        return DJSettings.from_dict(json.loads(row[0])), int(row[1]), str(row[2])

    @staticmethod
    def _session(tx, owner, session_id):
        row = tx.fetchone(
            'SELECT owner_profile_id,generation,settings,revision,defaults_revision,updated_at FROM djconnect_session_dj_settings WHERE session_id=?',
            (session_id,),
        )
        if row is None:
            return None
        if row[0] != owner:
            raise PermissionError('session_owner_changed')
        return {'session_id': session_id, 'generation': str(row[1]),
                'settings': DJSettings.from_dict(json.loads(row[2])).as_dict(),
                'revision': int(row[3]), 'defaults_revision': int(row[4]), 'updated_at': str(row[5])}

    @classmethod
    def _snapshot(cls, tx, owner, session_id=''):
        defaults, revision, updated_at = cls._defaults(tx, owner)
        return {'contract_version': 2, 'defaults': defaults.as_dict(),
                'defaults_revision': revision, 'updated_at': updated_at,
                'activated': revision > 0,
                'session': cls._session(tx, owner, session_id) if session_id else None}

    async def async_read(self, owner, *, session_id='', authorize):
        _identifier(owner)
        if session_id:
            _identifier(session_id)

        def read(tx):
            result = self._snapshot(tx, owner, session_id)
            return result

        return await self._async_in_transaction(
            read, authorize=authorize, finalize_authorize=authorize)

    async def async_operation_result(self, owner, *, operation_id, binding, now_ms, authorize):
        """Read original acceptance, without reapplying or creating an operation."""
        _identifier(owner)
        if type(binding) is not str or re.fullmatch(r'[a-f0-9]{64}', binding) is None:
            raise SettingsCommitError('invalid_settings_binding')
        try:
            created_ms = operation_created_ms(operation_id)
        except OperationError as exc:
            raise SettingsCommitError(exc.code) from None
        if type(now_ms) is not int or now_ms < 0:
            raise SettingsCommitError('invalid_settings_clock')
        key = hashlib.sha256(_json([owner, operation_id]).encode()).hexdigest()

        def read(tx):
            clock = max(int(datetime.now(UTC).timestamp()*1000), now_ms, tx.fetchone(
                'SELECT high_water_ms FROM djconnect_settings_clock WHERE singleton=1')[0])
            row = tx.fetchone('SELECT binding,expires_ms,receipt FROM djconnect_settings_operations WHERE operation_key=?',
                              (key,))
            if created_ms > clock + FUTURE_SKEW_MS:
                raise SettingsCommitError('operation_clock_unqualified')
            if row is not None:
                if row[0] != binding:
                    raise SettingsCommitError('operation_scope_changed')
                return {'phase': 'accepted', 'receipt': json.loads(row[2])}
            # Expired absence can never be interpreted as proof of rejection.
            return {'phase': 'unknown' if created_ms + LIFETIME_MS <= clock else 'not_accepted',
                    'operation_id': operation_id}

        return await self._async_in_transaction(
            read, authorize=authorize, finalize_authorize=authorize)

    async def async_accept_user_choice(
        self, owner, *, operation_id, binding, patch, expected_defaults_revision,
        now_ms, session: SessionSettingsContext | None = None, authorize,
        validate_choices=None, require_full_selection=False, initial_selection_guard=None,
    ):
        """Commit once; no HA API, Runtime mutation, synthesis or event publication."""
        _identifier(owner)
        _revision(expected_defaults_revision)
        if type(binding) is not str or re.fullmatch(r'[a-f0-9]{64}', binding) is None:
            raise SettingsCommitError('invalid_settings_binding')
        if type(now_ms) is not int or now_ms < 0:
            raise SettingsCommitError('invalid_settings_clock')
        # Validate the entire closed patch before reserving or touching storage.
        DJSettings().patched(patch)
        try:
            created_ms = operation_created_ms(operation_id)
        except OperationError as exc:
            raise SettingsCommitError(exc.code) from None
        key = hashlib.sha256(_json([owner, operation_id]).encode()).hexdigest()
        intent = {'patch': patch, 'expected_defaults_revision': expected_defaults_revision,
                  'session': {'id': session.session_id, 'generation': session.generation,
                              'expected_revision': session.expected_revision} if session else None}
        digest = hashlib.sha256(_json(intent).encode()).hexdigest()

        initial_acceptance = False
        complete_selection = set(patch) == {'persona', 'voice', 'gender', 'mood', 'presence'}

        def accept(tx):
            nonlocal initial_acceptance
            high_water = tx.fetchone('SELECT high_water_ms FROM djconnect_settings_clock WHERE singleton=1')[0]
            clock = max(int(datetime.now(UTC).timestamp()*1000), now_ms, int(high_water))
            expires = created_ms + LIFETIME_MS
            if created_ms > clock + FUTURE_SKEW_MS:
                raise SettingsCommitError('operation_clock_unqualified')
            if expires <= clock:
                raise SettingsCommitError('operation_expired')
            existing = tx.fetchone(
                'SELECT binding,digest,receipt FROM djconnect_settings_operations WHERE operation_key=?', (key,))
            if existing is not None:
                if existing[0] != binding:
                    raise SettingsCommitError('operation_scope_changed')
                if existing[1] != digest:
                    raise SettingsCommitError('operation_payload_conflict')
                return {**json.loads(existing[2]), 'replayed': True}
            current = self._snapshot(tx, owner, session.session_id if session else '')
            if current['defaults_revision'] != expected_defaults_revision:
                raise SettingsRevisionConflict(current)
            initial_acceptance = not current['activated']
            if initial_acceptance and require_full_selection and not complete_selection:
                raise SettingsCommitError('settings_migration_choice_required')
            defaults = DJSettings.from_dict(current['defaults'])
            selected = defaults.patched(patch)
            if validate_choices is not None:
                validate_choices(selected)
            live = None
            if session is not None:
                lifecycle = tx.fetchone(
                    'SELECT owner_profile_id,lifecycle_status FROM djconnect_persistent_sessions WHERE session_id=?',
                    (session.session_id,),
                )
                if not lifecycle or lifecycle != (owner, 'ACTIVE'):
                    raise SettingsCommitError('session_context_changed')
                previous = current['session']
                if previous is None:
                    if session.expected_revision != 0:
                        raise SettingsRevisionConflict(current)
                    effective, live_revision = session.effective, 0
                else:
                    if previous['generation'] != session.generation:
                        raise SettingsCommitError('session_generation_changed')
                    if previous['revision'] != session.expected_revision:
                        raise SettingsRevisionConflict(current)
                    effective = DJSettings.from_dict(previous['settings'])
                    live_revision = previous['revision']
                    if effective != session.effective:
                        raise SettingsCommitError('runtime_settings_not_reconciled')
                next_effective = effective.patched(patch)
                if validate_choices is not None:
                    validate_choices(next_effective)
                live = {'session_id': session.session_id, 'generation': session.generation,
                        'settings': next_effective.as_dict(),
                        'revision': live_revision + int(live_revision == 0 or next_effective != effective)}
                if next_effective.mood != effective.mood:
                    from .summary import mood_tx
                    stamp = datetime.fromtimestamp(clock / 1000, UTC).isoformat()
                    mood_tx(tx, session.session_id, next_effective.mood, stamp)
                    tx.execute('UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?',
                               (session.session_id,))
            tx.execute('DELETE FROM djconnect_settings_operations WHERE expires_ms<=?', (clock,))
            total = tx.fetchone('SELECT COUNT(*) FROM djconnect_settings_operations')[0]
            owned = tx.fetchone('SELECT COUNT(*) FROM djconnect_settings_operations WHERE owner_profile_id=?', (owner,))[0]
            if total >= MAX_RECORDS or owned >= MAX_OWNER_RECORDS:
                raise SettingsCommitError('settings_operation_capacity')
            revision = current['defaults_revision'] + int(not current['activated'] or selected != defaults)
            stamp = datetime.fromtimestamp(clock / 1000, UTC).isoformat()
            tx.execute(
                'INSERT INTO djconnect_profile_dj_settings VALUES (?,?,?,?) ON CONFLICT(owner_profile_id) DO UPDATE SET settings=excluded.settings,revision=excluded.revision,updated_at=excluded.updated_at',
                (owner, _json(selected.as_dict()), revision,
                 stamp if revision != current['defaults_revision'] else current['updated_at']),
            )
            if live is not None:
                tx.execute(
                    'INSERT INTO djconnect_session_dj_settings VALUES (?,?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET settings=excluded.settings,revision=excluded.revision,defaults_revision=excluded.defaults_revision,updated_at=excluded.updated_at',
                    (session.session_id, owner, session.generation, _json(live['settings']), live['revision'], revision, stamp),
                )
            result = {'operation_id': operation_id, 'accepted': True, 'replayed': False,
                      'expires_ms': expires, 'snapshot': self._snapshot(tx, owner, session.session_id if session else '')}
            tx.execute('INSERT INTO djconnect_settings_operations VALUES (?,?,?,?,?,?)',
                       (key, owner, binding, digest, expires, _json(result)))
            tx.execute('UPDATE djconnect_settings_clock SET high_water_ms=? WHERE singleton=1', (clock,))
            return result

        def final_admission():
            if not authorize():
                return False
            if created_ms + LIFETIME_MS <= max(now_ms, int(datetime.now(UTC).timestamp()*1000)):
                raise SettingsCommitError('operation_expired')
            # This callback runs on the HA loop after staging, never in the SQL
            # worker. A replay retains its original accepted migration decision.
            if (initial_acceptance and not complete_selection
                    and initial_selection_guard is not None and not initial_selection_guard()):
                raise SettingsCommitError('settings_migration_choice_required')
            return True

        return await self._async_in_transaction(
            accept, authorize=authorize, finalize_authorize=final_admission)

    async def async_accept_runtime_mood(self, owner, *, session, selected_mood,
                                       defaults_revision, authorize):
        """Automatic evolution shares acceptance but never remembers a default."""
        from .summary import mood_tx
        _identifier(owner)
        _revision(defaults_revision)
        next_settings = session.effective.patched({'mood': selected_mood})

        def accept(tx):
            lifecycle = tx.fetchone(
                'SELECT owner_profile_id,lifecycle_status FROM djconnect_persistent_sessions WHERE session_id=?',
                (session.session_id,))
            if lifecycle != (owner, 'ACTIVE'):
                raise SettingsCommitError('session_context_changed')
            current = self._session(tx, owner, session.session_id)
            if current is not None:
                if (current['generation'] != session.generation
                        or current['revision'] != session.expected_revision
                        or current['settings'] != session.effective.as_dict()):
                    raise SettingsCommitError('runtime_settings_not_reconciled')
            elif session.expected_revision != 0:
                raise SettingsCommitError('runtime_settings_not_reconciled')
            changed = next_settings != session.effective
            revision = session.expected_revision + int(changed)
            if changed:
                stamp = datetime.now(UTC).isoformat()
                mood_tx(tx, session.session_id, selected_mood, stamp)
                tx.execute('UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?',
                           (session.session_id,))
                tx.execute(
                    'INSERT INTO djconnect_session_dj_settings VALUES (?,?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET settings=excluded.settings,revision=excluded.revision,updated_at=excluded.updated_at',
                    (session.session_id, owner, session.generation, _json(next_settings.as_dict()),
                     revision, defaults_revision, stamp))
            return revision

        return await self._async_in_transaction(
            accept, authorize=authorize, finalize_authorize=authorize)

    async def async_purge_owner(self, owner):
        """Erase deleted identity preferences and dedup; never reassign them."""
        _identifier(owner)
        def erase(tx):
            for statement in (
                'DELETE FROM djconnect_profile_dj_settings WHERE owner_profile_id=?',
                'DELETE FROM djconnect_session_dj_settings WHERE owner_profile_id=?',
                'DELETE FROM djconnect_settings_operations WHERE owner_profile_id=?',
            ):
                tx.execute(statement, (owner,))
        await self._async_in_transaction(erase)

    async def async_purge_orphans(self, valid_owners):
        """Bound physical erasure after identity deletion/crash, not preference expiry."""
        owners = _json(sorted({_identifier(owner) for owner in valid_owners}))
        def erase(tx):
            for statement in (
                'DELETE FROM djconnect_profile_dj_settings WHERE owner_profile_id IN ('
                'SELECT DISTINCT owner_profile_id FROM djconnect_profile_dj_settings WHERE '
                'owner_profile_id NOT IN (SELECT value FROM json_each(?)) LIMIT 250)',
                'DELETE FROM djconnect_session_dj_settings WHERE owner_profile_id IN ('
                'SELECT DISTINCT owner_profile_id FROM djconnect_session_dj_settings WHERE '
                'owner_profile_id NOT IN (SELECT value FROM json_each(?)) LIMIT 250)',
                'DELETE FROM djconnect_settings_operations WHERE owner_profile_id IN ('
                'SELECT DISTINCT owner_profile_id FROM djconnect_settings_operations WHERE '
                'owner_profile_id NOT IN (SELECT value FROM json_each(?)) LIMIT 250)',
            ):
                tx.execute(statement, (owners,))
        await self._async_in_transaction(erase)

    async def async_export_defaults(self, owners, *, authorize):
        """One private owner snapshot; no effective Session, receipts or provider config."""
        owners = tuple(_identifier(owner) for owner in sorted(set(owners)))
        if not owners:
            return {}
        def read(tx):
            rows = tx.fetchall('SELECT owner_profile_id,settings,revision,updated_at '
                               'FROM djconnect_profile_dj_settings WHERE owner_profile_id IN '
                               '(SELECT value FROM json_each(?))', (_json(owners),))
            return {row[0]: {'contract_version': 2,
                            'values': DJSettings.from_dict(json.loads(row[1])).as_dict(),
                            'defaults_revision': int(row[2]), 'as_of': str(row[3])}
                    for row in rows}
        return await self._async_in_transaction(read, authorize=authorize,
                                                finalize_authorize=authorize)
