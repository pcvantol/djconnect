"""Transport-independent owner query contracts for historical projections."""

from __future__ import annotations

from contextvars import ContextVar

from .persistence.history import (
    HistoricalDJMomentProjection,
    HistoricalProjectionRepository,
    HistoricalSessionProjection,
)


_projection_ancestry = ContextVar("session_history_projection_ancestry", default=frozenset())

SUPPORTED_PROJECTION_VERSIONS = frozenset({1})


class HistoricalProjectionAccessDenied(PermissionError):
    """Raised when a caller tries to access another owner's history."""


class HistoricalProjectionVersionUnsupported(ValueError):
    """Raised when a durable projection cannot satisfy this app contract."""


class HistoricalProjectionQueryService:
    """Apply canonical owner-only history visibility above storage repositories."""

    def __init__(
        self,
        repository: HistoricalProjectionRepository,
        history_manager=None,
        source_validator=None,
        grant_revision=None,
    ) -> None:
        self._repository = repository
        self._conversation_history = history_manager
        self._source_validator = source_validator
        self._grant_revision = grant_revision
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

        if self._source_validator is not None and not await self._source_validator(owner, row):
            return None
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
        expected_role = "user" if row["kind"] == "conversation_user" else "assistant"
        if message.get("role") != expected_role:
            return None
        ancestry = _projection_ancestry.get()
        key = (owner, row["session_id"], row["entry_id"])
        if key in ancestry or len(ancestry) >= 20:
            return None
        # Explicit recursion state is passed through a task-local ContextVar below.
        token = _projection_ancestry.set(ancestry | {key})
        try:
            for target in message.get("historical_entry_references", []):
                try:
                    await self._session(owner, target["session_id"])
                except HistoricalProjectionAccessDenied:
                    return None
                source = await self._repository.async_entry_record(
                    owner, target["session_id"], target["entry_id"]
                )
                if source is None or await self._project_entry(owner, source) is None:
                    return None
        finally:
            _projection_ancestry.reset(token)
        entry.pop("conversation_reference", None)
        entry["origin_message_id"] = message["id"]
        entry["client_message_id"] = message.get("client_message_id")
        entry["text"] = str(message.get("text") or "")
        entry["turn_id"] = ref["turn_id"]
        entry["role"] = "user" if row["kind"] == "conversation_user" else "assistant"
        entry["input_type"] = message.get("session_turn", {}).get("input_type", "text")
        entry["context"] = message.get("session_turn", {}).get("context", {})
        for field in ("sources", "links", "historical_matches", "navigation_actions"):
            if isinstance(message.get(field), list):
                entry[field] = message[field][:20]
        return entry

    async def _revision_session(self, owner: str, session: dict) -> dict:
        suffix = (
            await self._conversation_history.async_scope_revision("profile:" + owner)
            if self._conversation_history
            else "0:0"
        )
        grant = await self._grant_revision(owner) if self._grant_revision else ""
        return {
            **session,
            "revision": str(session["revision"])
            + ":"
            + session["lifecycle_status"]
            + ":"
            + suffix
            + ":"
            + grant,
        }

    async def _session(self, owner: str, session_id: str) -> dict:
        from .session_history_projection import session_retained

        session = await self._repository.async_session_record(session_id)
        if not session or session["owner_profile_id"] != owner or not session_retained(session):
            raise HistoricalProjectionAccessDenied("session_unavailable")
        return await self._revision_session(owner, session)

    async def async_session_page(
        self, owner: str, *, limit: int = 20, cursor: str = "", include_active: bool = False
    ) -> dict:
        from .session_history_projection import (
            checked_limit,
            public_session,
            session_retained,
            HistoryQueryError,
        )

        checked_limit(limit)
        revision = await self._repository.async_owner_revision(owner, include_active=include_active)
        scope = {
            "profile_id": owner,
            "mode": "sessions",
            "revision": revision,
            "include_active": include_active,
            "paging_version": 2,
        }
        after = self._history_cursor.decode(cursor, scope) if cursor else None
        if after is not None and not isinstance(after, list):
            raise HistoryQueryError("invalid_history_cursor")
        rows = await self._repository.async_session_records(
            owner, limit=251, before=after, include_active=include_active
        )
        page = []
        last = None
        for row in rows[:250]:
            last = [row["created_at"], row["session_id"]]
            if session_retained(row):
                page.append(public_session(row))
            if len(page) >= limit:
                break
        more = bool(last and any([r["created_at"], r["session_id"]] < last for r in rows))
        if (
            await self._repository.async_owner_revision(owner, include_active=include_active)
            != revision
        ):
            raise HistoryQueryError("invalid_history_cursor")
        return {
            "success": True,
            "schema_version": 1,
            "sessions": page,
            "revision": revision,
            "next_cursor": self._history_cursor.encode(scope, last) if more else None,
            "coverage": "saved_sessions_keyset",
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
        from .session_history_projection import HistoryQueryError

        if (await self._session(owner, session_id))["revision"] != session["revision"]:
            raise HistoryQueryError("invalid_history_cursor")
        return {
            "success": True,
            "schema_version": 1,
            "session": public_session(session),
            "entries": visible,
            "revision": session["revision"],
            "next_cursor": self._history_cursor.encode(scope, last) if more else None,
            "coverage": "saved_entries_only",
        }

    async def async_timeline_window(
        self,
        owner: str,
        session_id: str,
        *,
        window: str,
        limit: int = 20,
        anchor_entry_id: str = "",
    ) -> dict:
        """Bounded revalidation window; fresh appends never require a first-page walk."""
        from .session_history_projection import checked_limit, public_session, HistoryQueryError

        checked_limit(limit)
        session = await self._session(owner, session_id)
        if window not in {"tail", "anchor"}:
            raise HistoryQueryError("invalid_history_window")
        if window == "anchor":
            anchor = (await self.async_open_entry(owner, session_id, anchor_entry_id))["entry"]
            # Include the retained anchor, then later accepted rows in canonical order.
            rows = await self._repository.async_entry_records(
                owner, session_id, after=anchor["order"] - 1
            )
        else:
            rows = await self._repository.async_entry_records(owner, session_id, descending=True)
        visible = []
        scanned = []
        for row in rows[:250]:
            scanned.append(row["order"])
            entry = await self._project_entry(owner, row)
            if entry is not None:
                visible.append(entry)
            if len(visible) >= limit:
                break
        visible.sort(key=lambda entry: entry["order"])
        if (await self._session(owner, session_id))["revision"] != session["revision"]:
            raise HistoryQueryError("invalid_history_cursor")
        return {
            "success": True,
            "schema_version": 1,
            "session": public_session(session),
            "entries": visible,
            "revision": session["revision"],
            "next_cursor": None,
            "coverage": "bounded_saved_entry_window",
            "window": window,
            "anchor_entry_id": anchor_entry_id if window == "anchor" else None,
            "scanned_order_min": min(scanned) if scanned else None,
            "scanned_order_max": max(scanned) if scanned else None,
            "scan_complete": len(scanned) == len(rows),
            "window_limit": limit,
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
        from .session_history_projection import HistoryQueryError

        if (await self._session(owner, session_id))["revision"] != session["revision"]:
            raise HistoryQueryError("invalid_history_cursor")
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
        grant = await self._grant_revision(owner) if self._grant_revision else ""
        initial_revision = await self._repository.async_owner_revision(owner, include_active=True)
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
        if (
            await self._grant_revision(owner) if self._grant_revision else ""
        ) != grant or await self._repository.async_owner_revision(
            owner, include_active=True
        ) != initial_revision:
            from .session_history_projection import HistoryQueryError

            raise HistoryQueryError("invalid_history_cursor")
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
