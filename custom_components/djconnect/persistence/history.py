"""Immutable renderer-safe historical Session and DJMoment projections."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4, uuid5, NAMESPACE_URL
from datetime import UTC, datetime, timedelta
import json

from .service import PersistenceRepository, PersistenceTransaction
from .sessions import PersistentSession



@dataclass(frozen=True)
class HistoricalSessionProjection:
    historical_session_id: str
    originating_session_id: str
    owner_profile_id: str
    lifecycle_outcome: str
    created_at: str
    projection_version: int = 1


@dataclass(frozen=True)
class HistoricalDJMomentProjection:
    """A durable, renderer-safe historical DJMoment projection."""

    historical_moment_id: str
    originating_session_id: str
    originating_moment_id: str
    owner_profile_id: str
    moment_type: str
    rendered_text: str
    presentation_metadata: str
    visibility: str
    ordering: int
    created_at: str
    projection_version: int = 1


class HistoricalProjectionRepository(PersistenceRepository):
    async def async_owner_revision(
        self, owner_profile_id: str, *, include_active: bool = False
    ) -> str:
        def read(tx):
            row = tx.fetchone(
                "SELECT COUNT(*),COALESCE(SUM(history_revision),0),COALESCE(MAX(updated_at),'') "
                "FROM djconnect_persistent_sessions WHERE owner_profile_id=? "
                "AND (? OR lifecycle_status IN ('ENDED','INTERRUPTED')) AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_persistent_sessions.owner_profile_id AND deletion.session_id=djconnect_persistent_sessions.session_id)",
                (owner_profile_id, int(include_active)),
            )
            return ":".join(str(v) for v in row)

        return await self._async_in_transaction(read)

    async def async_session_records(
        self, owner_profile_id: str, *, limit: int = 51, before=None, include_active: bool = False
    ) -> list[dict]:
        """Bounded keyset read: old pages are never silently lost behind a fixed window."""

        def read(tx):
            if before:
                query = (
                    "SELECT session_id,owner_profile_id,lifecycle_status,created_at,started_at,"
                    "ended_at,interrupted_at,history_revision,history_enabled "
                    "FROM djconnect_persistent_sessions WHERE owner_profile_id=? "
                    "AND (? OR lifecycle_status IN ('ENDED','INTERRUPTED')) "
                    "AND (created_at,session_id)<(?,?) "
                    "AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_persistent_sessions.owner_profile_id AND deletion.session_id=djconnect_persistent_sessions.session_id)" " ORDER BY created_at DESC,session_id DESC LIMIT ?"
                )
                parameters = (
                    owner_profile_id,
                    int(include_active),
                    *tuple(before),
                    min(251, limit),
                )
            else:
                query = (
                    "SELECT session_id,owner_profile_id,lifecycle_status,created_at,started_at,"
                    "ended_at,interrupted_at,history_revision,history_enabled "
                    "FROM djconnect_persistent_sessions WHERE owner_profile_id=? "
                    "AND (? OR lifecycle_status IN ('ENDED','INTERRUPTED')) "
                    "AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_persistent_sessions.owner_profile_id AND deletion.session_id=djconnect_persistent_sessions.session_id)" " ORDER BY created_at DESC,session_id DESC LIMIT ?"
                )
                parameters = (owner_profile_id, int(include_active), min(251, limit))
            rows = tx.fetchall(query, parameters)
            keys = (
                "session_id",
                "owner_profile_id",
                "lifecycle_status",
                "created_at",
                "started_at",
                "ended_at",
                "interrupted_at",
                "revision",
                "history_enabled",
            )
            from .summary import attach_tx

            return attach_tx(tx, [dict(zip(keys, row)) for row in rows])

        return await self._async_in_transaction(read)

    async def async_session_record(self, session_id: str) -> dict | None:
        def read(tx):
            row = tx.fetchone(
                "SELECT session_id,owner_profile_id,lifecycle_status,created_at,started_at,ended_at,interrupted_at,history_revision,history_enabled FROM djconnect_persistent_sessions WHERE session_id=? AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_persistent_sessions.owner_profile_id AND deletion.session_id=djconnect_persistent_sessions.session_id)",
                (session_id,),
            )
            keys = (
                "session_id",
                "owner_profile_id",
                "lifecycle_status",
                "created_at",
                "started_at",
                "ended_at",
                "interrupted_at",
                "revision",
                "history_enabled",
            )
            from .summary import attach_tx

            return attach_tx(tx, [dict(zip(keys, row))])[0] if row else None

        return await self._async_in_transaction(read)

    async def async_entry_records(
        self,
        owner_profile_id: str,
        session_id: str,
        *,
        after: int = 0,
        limit: int = 251,
        before: int | None = None,
        descending: bool = False,
        kind: str = "",
    ) -> list[dict]:
        def read(tx):
            # Both query shapes are fixed SQL; all cursor/owner/bound values bind as data.
            query = (
                "SELECT entry_id,session_id,entry_order,kind,reference_id,body,occurred_at,"
                "retained_until,visibility,revoked_at FROM djconnect_session_entries "
                "WHERE owner_profile_id=? AND session_id=? AND entry_order>? AND entry_order<? AND (?='' OR kind=?) "
                "AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_session_entries.owner_profile_id AND deletion.session_id=djconnect_session_entries.session_id)" " ORDER BY entry_order DESC LIMIT ?"
                if descending
                else "SELECT entry_id,session_id,entry_order,kind,reference_id,body,occurred_at,"
                "retained_until,visibility,revoked_at FROM djconnect_session_entries "
                "WHERE owner_profile_id=? AND session_id=? AND entry_order>? AND entry_order<? AND (?='' OR kind=?) "
                "AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_session_entries.owner_profile_id AND deletion.session_id=djconnect_session_entries.session_id)" " ORDER BY entry_order ASC LIMIT ?"
            )
            rows = tx.fetchall(
                query,
                (
                    owner_profile_id,
                    session_id,
                    after,
                    before if before is not None else 9223372036854775807,
                    kind,
                    kind,
                    min(251, limit),
                ),
            )
            keys = (
                "entry_id",
                "session_id",
                "order",
                "kind",
                "reference_id",
                "body",
                "occurred_at",
                "retained_until",
                "visibility",
                "revoked_at",
            )
            return [dict(zip(keys, row)) for row in rows]

        return await self._async_in_transaction(read)

    async def async_entry_record(
        self, owner_profile_id: str, session_id: str, entry_id: str
    ) -> dict | None:
        def read(tx):
            row = tx.fetchone(
                "SELECT entry_id,session_id,entry_order,kind,reference_id,body,occurred_at,retained_until,visibility,revoked_at FROM djconnect_session_entries WHERE owner_profile_id=? AND session_id=? AND entry_id=? AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_session_entries.owner_profile_id AND deletion.session_id=djconnect_session_entries.session_id)",
                (owner_profile_id, session_id, entry_id),
            )
            keys = (
                "entry_id",
                "session_id",
                "order",
                "kind",
                "reference_id",
                "body",
                "occurred_at",
                "retained_until",
                "visibility",
                "revoked_at",
            )
            return dict(zip(keys, row)) if row else None

        return await self._async_in_transaction(read)

    async def async_current_playback_entry(
        self, owner: str, session_id: str, item_id: str
    ) -> str | None:
        def read(tx):
            row = tx.fetchone(
                "SELECT entry_id,body FROM djconnect_session_entries WHERE owner_profile_id=? AND session_id=? AND kind='playback_observed' AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_session_entries.owner_profile_id AND deletion.session_id=djconnect_session_entries.session_id)" " ORDER BY entry_order DESC LIMIT 1",
                (owner, session_id),
            )
            if row is None:
                return None
            try:
                body = json.loads(row[1])
            except (TypeError, ValueError):
                return None
            return row[0] if isinstance(body, dict) and body.get("item_id") == item_id else None

        return await self._async_in_transaction(read)

    async def async_playback_records(self, owner_profile_id: str) -> list[dict]:
        def read(tx):
            rows = tx.fetchall(
                "SELECT e.entry_id,e.session_id,e.entry_order,e.kind,e.reference_id,e.body,e.occurred_at,e.retained_until,e.visibility,e.revoked_at FROM djconnect_session_entries e JOIN djconnect_persistent_sessions s ON s.session_id=e.session_id WHERE e.owner_profile_id=? AND e.kind='playback_observed' AND s.lifecycle_status IN ('ENDED','INTERRUPTED') AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=e.owner_profile_id AND deletion.session_id=e.session_id)" " ORDER BY e.occurred_at DESC,e.entry_id DESC LIMIT 251",
                (owner_profile_id,),
            )
            keys = (
                "entry_id",
                "session_id",
                "order",
                "kind",
                "reference_id",
                "body",
                "occurred_at",
                "retained_until",
                "visibility",
                "revoked_at",
            )
            return [dict(zip(keys, row)) for row in rows]

        return await self._async_in_transaction(read)

    async def async_append_entries(
        self, owner_profile_id: str, session_id: str, entries: list[dict], *, authorize=None
    ) -> list[str]:
        """One existing transaction for accepted projections; terminal archives reject writes."""

        return await self._async_in_transaction(
            lambda tx: self._append_entries_tx(tx, owner_profile_id, session_id, entries),
            authorize=authorize, finalize_authorize=authorize,
        )

    def _append_entries_tx(self, tx, owner_profile_id, session_id, entries):
        session = tx.fetchone(
            "SELECT owner_profile_id,lifecycle_status,history_enabled,history_revision FROM djconnect_persistent_sessions WHERE session_id=?",
            (session_id,),
        )
        if not session or session[0] != owner_profile_id:
            raise PermissionError("session_unavailable")
        if tx.fetchone('SELECT 1 FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND session_id=?',
                       (owner_profile_id, session_id)):
            raise PermissionError('session_unavailable')
        if session[1] != "ACTIVE":
            raise ValueError("session_context_changed")
        if not session[2]:
            return []
        last = tx.fetchone(
            "SELECT MAX(entry_order) FROM djconnect_session_entries WHERE session_id=?",
            (session_id,),
        )
        order = int(last[0] or 0)
        ids = []
        added = 0
        for item in entries:
            if tx.fetchone(
                'SELECT 1 FROM djconnect_content_tombstones WHERE owner_profile_id=? AND session_id=? '
                'AND reference_id IN (SELECT value FROM json_each(?))',
                (owner_profile_id, session_id, json.dumps(item.get('body', {}).get('dependency_moment_ids', []))),
            ):
                raise PermissionError('content_deleted')
            if tx.fetchone(
                'SELECT 1 FROM djconnect_content_tombstones WHERE owner_profile_id=? AND session_id=? AND reference_id=?',
                (owner_profile_id, session_id, item['reference_id']),
            ):
                raise PermissionError('content_deleted')
            if item["kind"] == "playback_observed":
                accepted = tx.fetchone(
                    "SELECT entry_id FROM djconnect_session_acceptances WHERE session_id=? AND kind=? AND reference_id=?",
                    (session_id, item["kind"], item["reference_id"]),
                )
                if accepted:
                    ids.append(str(accepted[0]))
                    continue
            existing = tx.fetchone(
                "SELECT entry_id FROM djconnect_session_entries WHERE session_id=? AND kind=? AND reference_id=?",
                (session_id, item["kind"], item["reference_id"]),
            )
            if existing:
                ids.append(str(existing[0]))
                continue
            if item["kind"] == "playback_observed":
                previous = tx.fetchone(
                    "SELECT entry_id,body FROM djconnect_session_entries WHERE session_id=? AND kind='playback_observed' ORDER BY entry_order DESC LIMIT 1",
                    (session_id,),
                )
                if previous and json.loads(previous[1]).get("item_id") == item["body"].get(
                    "item_id"
                ):
                    ids.append(str(previous[0]))
                    continue
            order += 1
            identifier = (
                "entry-"
                + uuid5(
                    NAMESPACE_URL, session_id + ":" + item["kind"] + ":" + item["reference_id"]
                ).hex
            )
            if item["kind"] == "playback_observed":
                from .summary import record_event_tx

                result, _ = record_event_tx(
                    tx, session_id, item["kind"], item["reference_id"], identifier
                )
                if result == "full":
                    order -= 1
                    continue
            stamp = item.get("occurred_at") or datetime.now(UTC).isoformat()
            # Active entries live with their Session, not with an independent
            # rolling clock. Terminal transition assigns the one Session cap.
            expires = "9999-12-31T00:00:00+00:00"
            tx.execute(
                "INSERT INTO djconnect_session_entries (entry_id,session_id,owner_profile_id,entry_order,kind,reference_id,body,occurred_at,retained_until,visibility) VALUES (?,?,?,?,?,?,?,?,?,'owner')",
                (
                    identifier,
                    session_id,
                    owner_profile_id,
                    order,
                    item["kind"],
                    item["reference_id"],
                    json.dumps(item["body"], ensure_ascii=False, sort_keys=True),
                    stamp,
                    expires,
                ),
            )
            ids.append(identifier)
            added += 1
        if added:
            tx.execute(
                "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+? WHERE session_id=?",
                (added, session_id),
            )
        return ids

    async def async_accept_moment(
        self, owner, session_id, moment_id, entry=None, *, authorize=None, finalize_authorize=None
    ):
        """Semantic commit independently qualified from optional archival text."""

        def accept(tx):
            row = tx.fetchone(
                "SELECT owner_profile_id,lifecycle_status,history_enabled FROM djconnect_persistent_sessions WHERE session_id=?",
                (session_id,),
            )
            if not row or row[0] != owner or row[1] != "ACTIVE":
                raise PermissionError("session_context_changed")
            if tx.fetchone(
                'SELECT 1 FROM djconnect_content_tombstones WHERE owner_profile_id=? AND session_id=? AND reference_id=?',
                (owner, session_id, moment_id),
            ):
                return False
            if tx.fetchone(
                'SELECT 1 FROM djconnect_content_tombstones WHERE owner_profile_id=? AND session_id=? '
                'AND reference_id IN (SELECT value FROM json_each(?))',
                (owner, session_id, json.dumps((entry or {}).get('body', {}).get('dependency_moment_ids', []))),
            ):
                return False
            if not row[2]:
                # Private-history opt-out does not disable existing live Moments.
                # Validate active ownership in this transaction without retaining
                # derived totals, replay keys or body under a revoked grant.
                return True
            old = tx.fetchone(
                "SELECT 1 FROM djconnect_session_acceptances WHERE session_id=? AND kind='dj_moment' AND reference_id=?",
                (session_id, moment_id),
            )
            if old:
                return False
            ids = self._append_entries_tx(tx, owner, session_id, [entry]) if entry else []
            from .summary import record_event_tx

            record_event_tx(tx, session_id, "dj_moment", moment_id, ids[0] if ids else "")
            if not ids:
                tx.execute(
                    "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?",
                    (session_id,),
                )
            return True

        return await self._async_in_transaction(accept, authorize=authorize, finalize_authorize=finalize_authorize)

    async def async_accept_mood(self, owner, session_id, mood, *, authorize=None):
        def accept(tx):
            row = tx.fetchone(
                "SELECT owner_profile_id,lifecycle_status FROM djconnect_persistent_sessions WHERE session_id=?",
                (session_id,),
            )
            if not row or row[0] != owner or row[1] != "ACTIVE":
                raise PermissionError("session_context_changed")
            from .summary import mood_tx

            mood_tx(tx, session_id, mood, datetime.now(UTC).isoformat())
            tx.execute(
                "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?",
                (session_id,),
            )

        await self._async_in_transaction(accept, authorize=authorize)

    async def _async_history_change(self, operation, *, authorize=None, **scope):
        """Fence the single RAM image owner across the destructive transaction."""
        media = getattr(self._persistence, "session_image_owner", None)
        speech = getattr(self._persistence, "session_speech_invalidator", None)
        if speech is not None:
            speech()
        token = media.begin_history_change(**scope) if media is not None else None
        try:
            if authorize is None:
                return await self._async_in_transaction(operation)
            return await self._async_in_transaction(operation, authorize=authorize,
                                                    finalize_authorize=authorize)
        finally:
            if speech is not None:
                speech()
            if media is not None:
                media.end_history_change(token, **scope)

    async def async_retention_policy(self) -> tuple[int, int]:
        return await self._async_in_transaction(lambda tx: tx.fetchone(
            "SELECT retention_days,revision FROM djconnect_session_retention WHERE singleton=1"))

    @property
    def retention_fence(self):
        return (getattr(self._persistence, 'history_retention_epoch', 0),
                getattr(self._persistence, 'history_retention_writes', 0))

    async def async_set_retention_days(self, days: int, *, authorize) -> tuple[int, int]:
        """Installation-wide private-history cap; caller supplies admin authority."""
        if type(days) is not int or not 1 <= days <= 90:
            raise ValueError("invalid_session_retention_days")
        if not callable(authorize):
            raise PermissionError("admin_authorization_required")
        def update(tx):
            current = tx.fetchone("SELECT retention_days,revision FROM djconnect_session_retention WHERE singleton=1")
            if current[0] == days:
                return current
            tx.execute("UPDATE djconnect_session_retention SET retention_days=?,revision=revision+1 WHERE singleton=1", (days,))
            tx.execute(
                "UPDATE djconnect_session_entries SET retained_until=MIN(retained_until,(SELECT strftime('%Y-%m-%dT%H:%M:%f+00:00',julianday(COALESCE(NULLIF(ended_at,''),NULLIF(interrupted_at,''),created_at))+?) FROM djconnect_persistent_sessions s WHERE s.session_id=djconnect_session_entries.session_id)) WHERE session_id IN (SELECT session_id FROM djconnect_persistent_sessions WHERE lifecycle_status IN ('ENDED','INTERRUPTED'))", (days,))
            tx.execute(
                "UPDATE djconnect_persistent_sessions SET history_enabled=0,history_revision=history_revision+1 WHERE history_enabled=1 AND lifecycle_status IN ('ENDED','INTERRUPTED') AND julianday(COALESCE(NULLIF(ended_at,''),NULLIF(interrupted_at,''),created_at))<=julianday(?) - ?",
                (datetime.now(UTC).isoformat(), min(days, current[0])))
            return days, current[1] + 1
        self._persistence.history_retention_epoch = self.retention_fence[0] + 1
        self._persistence.history_retention_writes = self.retention_fence[1] + 1
        try:
            return await self._async_history_change(update, authorize=authorize)
        finally:
            self._persistence.history_retention_writes -= 1
            self._persistence.history_retention_epoch += 1

    async def async_purge_profile_history(self, owner: str) -> None:
        """Erase the deleted owner's projections, never reassign them with devices."""

        def erase(tx):
            tx.execute(
                "DELETE FROM djconnect_session_summaries WHERE session_id IN (SELECT session_id FROM djconnect_persistent_sessions WHERE owner_profile_id=?)",
                (owner,),
            )
            tx.execute(
                "DELETE FROM djconnect_session_acceptances WHERE session_id IN (SELECT session_id FROM djconnect_persistent_sessions WHERE owner_profile_id=?)",
                (owner,),
            )
            tx.execute("DELETE FROM djconnect_session_entries WHERE owner_profile_id=?", (owner,))
            tx.execute(
                "DELETE FROM djconnect_historical_moments WHERE owner_profile_id=?", (owner,)
            )
            tx.execute(
                "DELETE FROM djconnect_historical_sessions WHERE owner_profile_id=?", (owner,)
            )
            tx.execute(
                "UPDATE djconnect_persistent_sessions SET history_enabled=0,history_revision=history_revision+1 WHERE owner_profile_id=? AND history_enabled=1",
                (owner,),
            )

        await self._async_history_change(erase, owner=owner)

    async def async_remove_entry_records(self, owner: str, identifiers: list[str]) -> None:
        """Withdraw source rows and invalidate affected query cursors atomically."""

        def erase(tx):
            affected = set()
            for identifier in identifiers[:250]:
                row = tx.fetchone(
                    "SELECT session_id,kind,body FROM djconnect_session_entries WHERE owner_profile_id=? AND entry_id=?",
                    (owner, identifier),
                )
                if row is not None:
                    affected.add(row[0])
                    body = json.loads(row[2])
                    if row[1] == 'dj_moment' and body.get('archive_basis') == 'owner_metadata_narration_v1':
                        from ..session_history_projection import publication_receipt
                        tx.execute("UPDATE djconnect_session_entries SET kind='dj_publication',body=? WHERE owner_profile_id=? AND entry_id=?",
                            (json.dumps(publication_receipt(body,'source_withdrawn')),owner,identifier))
                    else:
                        tx.execute(
                            "DELETE FROM djconnect_session_entries WHERE owner_profile_id=? AND entry_id=?",
                            (owner, identifier),
                        )
                    tx.execute(
                        "DELETE FROM djconnect_historical_moments WHERE owner_profile_id=? AND historical_moment_id=?",
                        (owner, identifier),
                    )
            for session_id in affected:
                from .summary import withdraw_tx

                withdraw_tx(tx, session_id)
                tx.execute(
                    "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=? AND owner_profile_id=?",
                    (session_id, owner),
                )

        await self._async_history_change(erase, owner=owner, identifiers=identifiers[:250])

    async def async_withdraw_source_entry(self, provider_entry_id: str) -> None:
        """Permanent revocation: scan bounded batches in one canonical transaction."""

        def erase(tx):
            after = ""
            affected = set()
            rows = tx.fetchall("SELECT session_id,source_binding FROM djconnect_session_summaries")
            for session_id, raw in rows:
                if json.loads(raw).get("provider_entry_id") == provider_entry_id:
                    affected.add(session_id)

            while True:
                rows = tx.fetchall(
                    "SELECT entry_id,session_id,body FROM djconnect_session_entries WHERE kind IN ('playback_observed','dj_moment') AND entry_id>? ORDER BY entry_id LIMIT 250",
                    (after,),
                )
                if not rows:
                    break
                after = rows[-1][0]
                for identifier, session_id, raw in rows:
                    try:
                        context = json.loads(raw).get("source_context", {})
                    except (TypeError, ValueError, AttributeError):
                        continue
                    if context.get("provider_entry_id") == provider_entry_id:
                        body = json.loads(raw)
                        if body.get('archive_basis') == 'owner_metadata_narration_v1':
                            from ..session_history_projection import publication_receipt
                            tx.execute("UPDATE djconnect_session_entries SET kind='dj_publication',body=? WHERE entry_id=?",
                                (json.dumps(publication_receipt(body,'source_withdrawn')),identifier))
                        else:
                            tx.execute("DELETE FROM djconnect_session_entries WHERE entry_id=?", (identifier,))
                        affected.add(session_id)
                if len(rows) < 250:
                    break
            for session_id in affected:
                from .summary import withdraw_tx

                withdraw_tx(tx, session_id)
                tx.execute(
                    "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?",
                    (session_id,),
                )

        await self._async_history_change(erase, provider_entry_id=provider_entry_id)

    async def async_playback_maintenance_records(
        self, *, after: str = "", limit: int = 250
    ) -> list[dict]:
        """Bounded stable-ID scan includes active observations for source withdrawal."""

        def read(tx):
            rows = tx.fetchall(
                "SELECT entry_id,session_id,owner_profile_id,kind,body FROM djconnect_session_entries WHERE kind IN ('playback_observed','dj_moment') AND entry_id>? ORDER BY entry_id LIMIT ?",
                (after, min(limit, 250)),
            )
            return [
                dict(zip(("entry_id", "session_id", "owner_profile_id", "kind", "body"), row))
                for row in rows
            ]

        return await self._async_in_transaction(read)

    async def async_cleanup_expired(
        self, *, cutoff: str, batch_size: int, entry_deadline: str | None = None
    ) -> tuple[int, int, int, int]:
        """Delete expired Moments before Sessions, plus expired orphan Moments."""
        # Fence only entry grants covered by this destructive retention pass.
        now = datetime.fromisoformat(entry_deadline) if entry_deadline else datetime.now(UTC)

        def cleanup(tx: PersistenceTransaction) -> tuple[int, int, int, int]:
            # Entry deadlines are independent of the final Session header date.
            now = datetime.fromisoformat(entry_deadline) if entry_deadline else datetime.now(UTC)
            expired = tx.fetchall(
                "SELECT entry_id,owner_profile_id,session_id,kind FROM djconnect_session_entries WHERE retained_until<=? ORDER BY retained_until,entry_id LIMIT ?",
                (now.isoformat(), batch_size),
            )
            affected = set()
            expired_sources = set()
            for identifier, owner, session_id, kind in expired:
                if kind == "playback_observed":
                    expired_sources.add(session_id)
                tx.execute(
                    "DELETE FROM djconnect_session_entries WHERE entry_id=? AND owner_profile_id=?",
                    (identifier, owner),
                )
                tx.execute(
                    "DELETE FROM djconnect_historical_moments WHERE historical_moment_id=? AND owner_profile_id=?",
                    (identifier, owner),
                )
                affected.add(session_id)
            for session_id in affected:
                from .summary import withdraw_tx

                if session_id in expired_sources:
                    withdraw_tx(tx, session_id)
                tx.execute(
                    "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?",
                    (session_id,),
                )
            orphan_rows = tx.fetchall(
                "SELECT historical_moment_id FROM djconnect_historical_moments "
                "WHERE created_at < ? AND NOT EXISTS (SELECT 1 FROM djconnect_historical_sessions "
                "WHERE originating_session_id=djconnect_historical_moments.originating_session_id) "
                "ORDER BY created_at, historical_moment_id LIMIT ?",
                (cutoff, batch_size),
            )
            for row in orphan_rows:
                tx.execute(
                    "DELETE FROM djconnect_historical_moments WHERE historical_moment_id=?",
                    (row[0],),
                )
            session_rows = tx.fetchall(
                "SELECT originating_session_id FROM djconnect_historical_sessions WHERE created_at < ? "
                "ORDER BY created_at, historical_session_id LIMIT ?",
                (cutoff, batch_size),
            )
            deleted_moments = len(orphan_rows)
            for row in session_rows:
                session_id = str(row[0])
                moments = tx.fetchall(
                    "SELECT historical_moment_id FROM djconnect_historical_moments "
                    "WHERE originating_session_id=?",
                    (session_id,),
                )
                for moment in moments:
                    tx.execute(
                        "DELETE FROM djconnect_historical_moments WHERE historical_moment_id=?",
                        (moment[0],),
                    )
                deleted_moments += len(moments)
                tx.execute(
                    "DELETE FROM djconnect_historical_sessions WHERE originating_session_id=?",
                    (session_id,),
                )
                tx.execute(
                    "DELETE FROM djconnect_session_entries WHERE session_id=?", (session_id,)
                )
                tx.execute(
                    "DELETE FROM djconnect_session_summaries WHERE session_id=?", (session_id,)
                )
                tx.execute(
                    "DELETE FROM djconnect_session_acceptances WHERE session_id=?", (session_id,)
                )
                tx.execute(
                    "UPDATE djconnect_persistent_sessions SET history_enabled=0,history_revision=history_revision+1 WHERE session_id=?",
                    (session_id,),
                )
            return len(session_rows), deleted_moments, len(orphan_rows), len(session_rows)

        return await self._async_history_change(cleanup, expired_before=now.timestamp(), session_cutoff=datetime.fromisoformat(cutoff).timestamp())

    def _project_terminal_tx(
        self, tx: PersistenceTransaction, session: PersistentSession
    ) -> HistoricalSessionProjection | None:
        """Existing aggregate/header and accepted qualified projections, one transaction."""
        policy = tx.fetchone(
            "SELECT history_enabled,owner_profile_id,lifecycle_status "
            "FROM djconnect_persistent_sessions WHERE session_id=?",
            (session.session_id,),
        )
        # A delayed Runtime must not recreate an erased Session's legacy
        # projection. The durable header, owner and terminal state authorize it.
        if (policy is None or not policy[0] or policy[1] != session.owner_profile_id
                or policy[2] not in {"ENDED", "INTERRUPTED"}
                or policy[2] != session.lifecycle_status):
            return None
        if tx.fetchone('SELECT 1 FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND session_id=?',
                       (session.owner_profile_id, session.session_id)):
            return None
        retention = tx.fetchone("SELECT retention_days FROM djconnect_session_retention WHERE singleton=1")[0]
        terminal = session.ended_at or session.interrupted_at or session.created_at
        deadline = (datetime.fromisoformat(terminal) + timedelta(days=retention)).isoformat()
        tx.execute("UPDATE djconnect_session_entries SET retained_until=MIN(retained_until,?) WHERE session_id=?",
                   (deadline, session.session_id))
        existing = tx.fetchone(
            "SELECT historical_session_id,originating_session_id,owner_profile_id,lifecycle_outcome,created_at,projection_version FROM djconnect_historical_sessions WHERE originating_session_id=?",
            (session.session_id,),
        )
        if existing is not None:
            return self._session_from_row(existing)
        projection = HistoricalSessionProjection(
            f"history-{uuid4().hex}",
            session.session_id,
            session.owner_profile_id,
            session.lifecycle_status,
            session.ended_at or session.interrupted_at or session.created_at,
        )
        tx.execute(
            "INSERT INTO djconnect_historical_sessions (historical_session_id,originating_session_id,owner_profile_id,lifecycle_outcome,started_at,ended_at,interrupted_at,interruption_reason,start_strategy,session_mood,session_direction,created_at,projection_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (
                projection.historical_session_id,
                session.session_id,
                session.owner_profile_id,
                session.lifecycle_status,
                session.started_at,
                session.ended_at,
                session.interrupted_at,
                session.interruption_reason,
                session.start_strategy,
                session.initial_mood,
                session.initial_direction,
                projection.created_at,
            ),
        )
        rows = tx.fetchall(
            "SELECT entry_id,reference_id,body,entry_order,occurred_at FROM djconnect_session_entries WHERE session_id=? AND kind='dj_moment' AND visibility='owner' AND revoked_at='' ORDER BY entry_order",
            (session.session_id,),
        )
        for entry_id, reference, raw, order, stamp in rows:
            body = json.loads(raw)
            if body.get("archive_basis") not in {
                "cc0_normalized_fields_v1",
                "runtime_authored_direction_v1",
                "runtime_accepted_settings_v1",
                "public_artist_narration_v1",
            }:
                continue
            tx.execute(
                "INSERT OR IGNORE INTO djconnect_historical_moments (historical_moment_id,originating_session_id,originating_moment_id,owner_profile_id,moment_type,rendered_text,presentation_metadata,visibility,ordering,created_at,projection_version) VALUES (?,?,?,?,?,?,?,'owner',?,?,1)",
                (
                    entry_id,
                    session.session_id,
                    reference,
                    session.owner_profile_id,
                    body["moment_type"],
                    body["text"],
                    json.dumps(
                        {
                            "archive_basis": body["archive_basis"],
                            "source_attribution": body.get("source_attribution", {}),
                            **({"sources":body["sources"]} if body.get("archive_basis") == "public_artist_narration_v1" else {}),
                        },
                        sort_keys=True,
                    ),
                    order,
                    stamp,
                ),
            )
        return projection

    async def async_project_session(
        self, session: PersistentSession
    ) -> HistoricalSessionProjection | None:
        return await self._async_in_transaction(lambda tx: self._project_terminal_tx(tx, session))

    async def async_project_moment(
        self,
        *,
        session_id: str,
        moment_id: str,
        owner_profile_id: str,
        moment_type: str,
        rendered_text: str,
        presentation_metadata: str,
        ordering: int,
        created_at: str,
        visibility: str = "owner",
    ) -> str | None:
        """Persist one already-canonical renderer-safe Moment projection once."""
        identifier = f"historical-moment-{uuid4().hex}"

        def write(tx: PersistenceTransaction) -> str | None:
            header = tx.fetchone(
                "SELECT owner_profile_id,history_enabled FROM djconnect_persistent_sessions "
                "WHERE session_id=?", (session_id,))
            if header is None or header[0] != owner_profile_id or not header[1]:
                return None
            if tx.fetchone('SELECT 1 FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND session_id=?',
                           (owner_profile_id, session_id)):
                return None
            if tx.fetchone(
                'SELECT 1 FROM djconnect_content_tombstones WHERE owner_profile_id=? AND session_id=? AND reference_id=?',
                (owner_profile_id, session_id, moment_id),
            ):
                return None
            existing = tx.fetchone(
                "SELECT historical_moment_id FROM djconnect_historical_moments "
                "WHERE originating_session_id=? AND originating_moment_id=?",
                (session_id, moment_id),
            )
            if existing is not None:
                return str(existing[0])
            tx.execute(
                "INSERT INTO djconnect_historical_moments "
                "(historical_moment_id, originating_session_id, originating_moment_id, owner_profile_id, "
                "moment_type, rendered_text, presentation_metadata, visibility, ordering, created_at, "
                "projection_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (
                    identifier,
                    session_id,
                    moment_id,
                    owner_profile_id,
                    moment_type,
                    rendered_text,
                    presentation_metadata,
                    visibility,
                    ordering,
                    created_at,
                ),
            )
            return identifier

        return await self._async_in_transaction(write)

    async def async_get_session(
        self, historical_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one historical Session projection without applying policy."""
        return await self._async_in_transaction(
            lambda tx: self._optional_session(
                tx.fetchone(
                    "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                    "lifecycle_outcome, created_at, projection_version "
                    "FROM djconnect_historical_sessions WHERE historical_session_id=? AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_historical_sessions.owner_profile_id AND deletion.session_id=djconnect_historical_sessions.originating_session_id)",
                    (historical_session_id,),
                )
            )
        )

    async def async_get_session_for_originating_id(
        self, originating_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one historical Session by its durable source identifier."""
        return await self._async_in_transaction(
            lambda tx: self._optional_session(
                tx.fetchone(
                    "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                    "lifecycle_outcome, created_at, projection_version "
                    "FROM djconnect_historical_sessions WHERE originating_session_id=? AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_historical_sessions.owner_profile_id AND deletion.session_id=djconnect_historical_sessions.originating_session_id)",
                    (originating_session_id,),
                )
            )
        )

    async def async_list_sessions_for_owner(
        self, owner_profile_id: str
    ) -> tuple[HistoricalSessionProjection, ...]:
        """Load one owner's Sessions in canonical recent-first order."""
        return await self._async_in_transaction(
            lambda tx: tuple(
                self._session_from_row(row)
                for row in tx.fetchall(
                    "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                    "lifecycle_outcome, created_at, projection_version "
                    "FROM djconnect_historical_sessions WHERE owner_profile_id=? "
                    "AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_historical_sessions.owner_profile_id AND deletion.session_id=djconnect_historical_sessions.originating_session_id)" " ORDER BY created_at DESC, historical_session_id DESC",
                    (owner_profile_id,),
                )
            )
        )

    async def async_get_moment(
        self, historical_moment_id: str
    ) -> HistoricalDJMomentProjection | None:
        """Load one historical DJMoment projection without applying policy."""
        return await self._async_in_transaction(
            lambda tx: self._optional_moment(
                tx.fetchone(
                    "SELECT historical_moment_id, originating_session_id, originating_moment_id, owner_profile_id, moment_type, rendered_text, presentation_metadata, visibility, ordering, created_at, projection_version FROM djconnect_historical_moments" " WHERE historical_moment_id=? AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_historical_moments.owner_profile_id AND deletion.session_id=djconnect_historical_moments.originating_session_id)",
                    (historical_moment_id,),
                )
            )
        )

    async def async_list_moments_for_session(
        self, originating_session_id: str
    ) -> tuple[HistoricalDJMomentProjection, ...]:
        """Load one Session's Moments in canonical renderer order."""
        return await self._async_in_transaction(
            lambda tx: tuple(
                self._moment_from_row(row)
                for row in tx.fetchall(
                    "SELECT historical_moment_id, originating_session_id, originating_moment_id, owner_profile_id, moment_type, rendered_text, presentation_metadata, visibility, ordering, created_at, projection_version FROM djconnect_historical_moments" " WHERE originating_session_id=? "
                    "AND " "NOT EXISTS (SELECT 1 FROM djconnect_history_deletion_targets AS deletion WHERE deletion.owner_profile_id=djconnect_historical_moments.owner_profile_id AND deletion.session_id=djconnect_historical_moments.originating_session_id)" " ORDER BY ordering ASC, created_at ASC, historical_moment_id ASC",
                    (originating_session_id,),
                )
            )
        )

    @staticmethod
    def _session_from_row(row: tuple[object, ...]) -> HistoricalSessionProjection:
        return HistoricalSessionProjection(
            *(str(value) if index < 5 else int(value) for index, value in enumerate(row))
        )

    @classmethod
    def _optional_session(
        cls, row: tuple[object, ...] | None
    ) -> HistoricalSessionProjection | None:
        return cls._session_from_row(row) if row is not None else None

    @staticmethod
    def _moment_from_row(row: tuple[object, ...]) -> HistoricalDJMomentProjection:
        return HistoricalDJMomentProjection(
            *(str(value) if index < 10 else int(value) for index, value in enumerate(row))
        )

    @classmethod
    def _optional_moment(
        cls, row: tuple[object, ...] | None
    ) -> HistoricalDJMomentProjection | None:
        return cls._moment_from_row(row) if row is not None else None
