"""Transport-independent owner query contracts for historical projections."""

from __future__ import annotations

from .persistence.history import (
    HistoricalDJMomentProjection,
    HistoricalProjectionRepository,
    HistoricalSessionProjection,
)


SUPPORTED_PROJECTION_VERSIONS = frozenset({1})


class HistoricalProjectionAccessDenied(PermissionError):
    """Raised when a caller tries to access another owner's history."""


class HistoricalProjectionVersionUnsupported(ValueError):
    """Raised when a durable projection cannot satisfy this app contract."""


class HistoricalProjectionQueryService:
    """Apply canonical owner-only history visibility above storage repositories."""

    def __init__(self, repository: HistoricalProjectionRepository, history_manager=None) -> None:
        self._repository = repository
        self._conversation_history = history_manager
        from .session_history_projection import HistoryCursorCodec
        self._history_cursor = HistoryCursorCodec()


    async def async_get_session(
        self, requester_profile_id: str, historical_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one owner-visible historical Session by its projection ID."""
        projection = await self._repository.async_get_session(historical_session_id)
        return self._authorize_session(requester_profile_id, projection)

    async def async_get_owner_session(
        self, requester_profile_id: str, originating_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one owner-visible historical Session by its source Session ID."""
        projection = await self._repository.async_get_session_for_originating_id(
            originating_session_id
        )
        return self._authorize_session(requester_profile_id, projection)

    async def async_list_recent_owner_sessions(
        self, requester_profile_id: str
    ) -> tuple[HistoricalSessionProjection, ...]:
        """List an owner's historical Sessions in canonical recent-first order."""
        projections = await self._repository.async_list_sessions_for_owner(requester_profile_id)
        return tuple(
            self._authorize_session(requester_profile_id, projection)
            for projection in projections
            if projection is not None
        )

    async def async_get_moment(
        self, requester_profile_id: str, historical_moment_id: str
    ) -> HistoricalDJMomentProjection | None:
        """Load one owner-visible, owner-only historical DJMoment."""
        projection = await self._repository.async_get_moment(historical_moment_id)
        return self._authorize_moment(requester_profile_id, projection)

    async def async_list_session_moments(
        self, requester_profile_id: str, historical_session_id: str
    ) -> tuple[HistoricalDJMomentProjection, ...]:
        """List owner-visible DJMoments for one owner-visible historical Session."""
        session = await self.async_get_session(requester_profile_id, historical_session_id)
        if session is None:
            return ()
        projections = await self._repository.async_list_moments_for_session(
            session.originating_session_id
        )
        return tuple(
            self._authorize_moment(requester_profile_id, projection)
            for projection in projections
            if projection is not None
        )

    async def _project_entry(self, owner: str, row: dict) -> dict | None:
        from .session_history_projection import project_entry

        entry = project_entry(row)
        if entry is None or "conversation_reference" not in entry:
            return entry
        ref = entry["conversation_reference"]
        if not self._conversation_history or ref.get("history_scope") != "profile:" + owner:
            return None
        messages = await self._conversation_history.async_messages_by_id(
            "profile:" + owner, {str(ref.get("message_id") or "")}
        )
        message = messages.get(ref.get("message_id"))
        if not message or message.get("session_turn", {}).get("turn_id") != ref.get("turn_id"):
            return None
        for target in message.get("historical_entry_references", []):
            source = await self._repository.async_entry_record(
                owner, target["session_id"], target["entry_id"]
            )
            if source is None or project_entry(source) is None:
                return None
        entry.pop("conversation_reference",None)
        entry["origin_message_id"]=message["id"]
        entry["client_message_id"]=message.get("client_message_id")
        entry["text"] = str(message.get("text") or "")
        entry["turn_id"] = ref["turn_id"]
        entry["role"] = "user" if row["kind"] == "conversation_user" else "assistant"
        entry["input_type"] = message.get("session_turn", {}).get("input_type", "text")
        entry["context"] = message.get("session_turn", {}).get("context", {})
        return entry


    async def _revision_session(self, owner: str, session: dict) -> dict:
        if self._conversation_history:
            session = {
                **session,
                "revision": str(session["revision"])
                + ":"
                + await self._conversation_history.async_scope_revision("profile:" + owner),
            }
        return session


    async def _session(self, owner: str, session_id: str) -> dict:
        from .session_history_projection import session_retained

        session = await self._repository.async_session_record(session_id)
        if not session or session["owner_profile_id"] != owner or not session_retained(session):
            raise HistoricalProjectionAccessDenied("session_unavailable")
        return await self._revision_session(owner, session)


    async def async_session_page(
        self, owner: str, *, limit: int = 20, cursor: str = "", include_active: bool = False
    ) -> dict:
        from .session_history_projection import checked_limit, public_session, session_retained

        checked_limit(limit)
        sessions = [
            s
            for s in await self._repository.async_session_records(owner)
            if session_retained(s)
            and (include_active or s["lifecycle_status"] in {"ENDED", "INTERRUPTED"})
        ]
        import hashlib

        digest = hashlib.sha256(
            str([(s["session_id"], s["revision"], s["lifecycle_status"]) for s in sessions]).encode()
        ).hexdigest()[:24]
        scope = {
            "profile_id": owner,
            "mode": "sessions",
            "revision": digest,
            "include_active": include_active,
        }
        after = self._history_cursor.decode(cursor, scope) if cursor else 0
        page = sessions[after : after + limit]
        more = after + limit < len(sessions)
        return {
            "success": True,
            "schema_version": 1,
            "sessions": [public_session(s) for s in page],
            "revision": digest,
            "next_cursor": self._history_cursor.encode(scope, after + len(page)) if more else None,
            "coverage": "bounded_saved_sessions",
            "retention_days": 90,
        }


    async def async_timeline_page(
        self, owner: str, session_id: str, *, limit: int = 20, cursor: str = ""
    ) -> dict:
        from .session_history_projection import (
            checked_limit,
            public_session,
            revision_scope,
        )

        checked_limit(limit)
        session = await self._session(owner, session_id)
        scope = revision_scope(owner, session, "timeline")
        after = self._history_cursor.decode(cursor, scope) if cursor else 0
        rows = await self._repository.async_entry_records(owner, session_id, after=after)
        visible = []
        last = after
        for row in rows[:250]:
            last = row["order"]
            entry = await self._project_entry(owner, row)
            if entry is not None:
                visible.append(entry)
            if len(visible) >= limit:
                break
        more = any(r["order"] > last for r in rows)
        return {
            "success": True,
            "schema_version": 1,
            "session": public_session(session),
            "entries": visible,
            "revision": session["revision"],
            "next_cursor": self._history_cursor.encode(scope, last) if more else None,
            "coverage": "saved_entries_only",
        }


    async def async_search_entries(
        self, owner: str, session_id: str, query: str, *, limit: int = 20, cursor: str = ""
    ) -> dict:
        from .session_history_projection import (
            checked_limit,
            revision_scope,
            text_highlights,
            HistoryQueryError,
        )

        checked_limit(limit)
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise HistoryQueryError("invalid_history_search")
        session = await self._session(owner, session_id)
        scope = revision_scope(owner, session, "search", query)
        after = self._history_cursor.decode(cursor, scope) if cursor else 0
        rows = await self._repository.async_entry_records(owner, session_id, after=after)
        matches = []
        last = after
        for row in rows[:250]:
            last = row["order"]
            entry = await self._project_entry(owner, row)
            marks = text_highlights(entry.get("text", ""), query) if entry else []
            if marks:
                matches.append({**entry, "highlights": marks})
            if len(matches) >= limit:
                break
        more = any(r["order"] > last for r in rows)
        return {
            "success": True,
            "schema_version": 1,
            "session_id": session_id,
            "query": query,
            "revision": session["revision"],
            "matches": matches,
            "returned_count": len(matches),
            "total_count": len(matches) if not cursor and not more else None,
            "complete": not more,
            "next_cursor": self._history_cursor.encode(scope, last) if more else None,
            "normalization": "NFKC-casefold",
            "highlight_units": "utf16",
        }


    async def async_open_entry(self, owner: str, session_id: str, entry_id: str) -> dict:
        from .session_history_projection import public_session

        session = await self._session(owner, session_id)
        # Anchor reads are scoped directly; they do not traverse unbounded timelines.
        row = await self._repository.async_entry_record(owner, session_id, entry_id)
        entry = await self._project_entry(owner, row) if row else None
        if entry is None:
            raise HistoricalProjectionAccessDenied("entry_unavailable")
        return {
            "success": True,
            "schema_version": 1,
            "session": public_session(session),
            "entry": entry,
            "read_only": session["lifecycle_status"] in {"ENDED", "INTERRUPTED"},
            "navigation_only": True,
        }


    async def async_find_playback(
        self, owner: str, *, artist: str = "", title: str = "", album: str = "", limit: int = 20
    ) -> dict:
        from .session_history_projection import checked_limit, normalize_text

        checked_limit(limit)
        matches = []
        rows = await self._repository.async_playback_records(owner)
        for row in rows[:250]:
            try:
                await self._session(owner, row["session_id"])
            except HistoricalProjectionAccessDenied:
                continue
            entry = await self._project_entry(owner, row)
            if not entry:
                continue
            fields = entry["playback"]
            if any(
                wanted and normalize_text(wanted) not in normalize_text(str(fields.get(key) or ""))
                for key, wanted in [("artist", artist), ("title", title), ("album", album)]
            ):
                continue
            matches.append(
                {
                    **entry,
                    "open_action": {
                        "kind": "open_session",
                        "session_id": row["session_id"],
                        "entry_id": row["entry_id"],
                        "navigation_only": True,
                    },
                }
            )
            if len(matches) >= limit:
                break
        return {
            "success": True,
            "schema_version": 1,
            "matches": matches,
            "coverage": "saved_observed_playback_only",
            "full_listens_proven": False,
            "repeat_counts_supported": False,
            "complete": len(rows) <= 250 and len(matches) < limit,
        }
    @staticmethod
    def _authorize_session(
        requester_profile_id: str, projection: HistoricalSessionProjection | None
    ) -> HistoricalSessionProjection | None:
        if projection is None:
            return None
        HistoricalProjectionQueryService._authorize_owner(
            requester_profile_id, projection.owner_profile_id
        )
        HistoricalProjectionQueryService._ensure_supported_version(projection.projection_version)
        return projection

    @staticmethod
    def _authorize_moment(
        requester_profile_id: str, projection: HistoricalDJMomentProjection | None
    ) -> HistoricalDJMomentProjection | None:
        if projection is None:
            return None
        HistoricalProjectionQueryService._authorize_owner(
            requester_profile_id, projection.owner_profile_id
        )
        if projection.visibility != "owner":
            raise HistoricalProjectionAccessDenied("historical_moment_visibility_not_supported")
        HistoricalProjectionQueryService._ensure_supported_version(projection.projection_version)
        return projection

    @staticmethod
    def _authorize_owner(requester_profile_id: str, owner_profile_id: str) -> None:
        if requester_profile_id != owner_profile_id:
            raise HistoricalProjectionAccessDenied("historical_projection_owner_mismatch")

    @staticmethod
    def _ensure_supported_version(projection_version: int) -> None:
        if projection_version not in SUPPORTED_PROJECTION_VERSIONS:
            raise HistoricalProjectionVersionUnsupported(
                f"unsupported_historical_projection_version:{projection_version}"
            )
