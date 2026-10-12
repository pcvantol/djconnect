"""Bounded mutable active-session projection; no provider/Planner work on reads."""
from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .forecast_expression import realize

VERSION = 1
PATH = '/api/djconnect/v1/session/forecast/{session_id}'
FRESHNESS_SECONDS = 120
REFRESH_INTERVAL_SECONDS = 30


def capability() -> dict[str, Any]:
    return {'available': True, 'version': VERSION, 'path': PATH, 'method': 'GET',
            'authentication': 'paired_device_bearer', 'scope': 'active_device_bound_owner_session',
            'live_field': 'session_forecast', 'live_event': 'forecast_changed',
            'nominal_window_seconds': 900, 'history': False,
            'imagery_roles': ['current', 'contextual', 'qualified_upcoming'],
            'emitted_imagery_roles': ['current'], 'qualified_upcoming_media': False}


def timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


@dataclass
class ForecastProjection:
    """Stored realized projection and original deadline; reads are pure."""

    session_id: str
    revision: int = 0
    value: dict[str, Any] = field(default_factory=dict)
    signature: str = ''
    context_item_id: str = ''
    deadline: float = 0
    refreshed_at: float = 0
    observation_deadline: float = 0
    observation_wall_deadline: float = 0
    expired: bool = False
    withdrawn: bool = False
    authority: Any = field(default=lambda: True, repr=False)
    clock: Any = field(default=time.monotonic, repr=False)
    wall_clock: Any = field(default=time.time, repr=False)

    def accept_observation(self) -> None:
        """Only an accepted provider observation renews current-context authority."""
        self.observation_deadline = self.clock() + FRESHNESS_SECONDS
        self.observation_wall_deadline = self.wall_clock() + FRESHNESS_SECONDS

    def update(self, semantic: dict, *, locale: str, persona: str,
               imagery: tuple[dict, ...] = (), current_item_id: str = "", force: bool = False) -> bool:
        if not self.authority():
            return False
        now = self.clock()
        if now >= self.observation_deadline:
            return self.tick()
        was_withdrawn = self.withdrawn or self.value.get('state') == 'withdrawn'
        self.withdrawn = False
        signature = hashlib.sha256(json.dumps([semantic, locale, persona, imagery, current_item_id],
                                               sort_keys=True).encode()).hexdigest()
        if not force and signature == self.signature and not self.expired and not was_withdrawn and (self.observation_deadline <= self.deadline or now - self.refreshed_at < REFRESH_INTERVAL_SECONDS):
            return False
        summary, sections = realize(semantic, locale, persona)
        self.revision += 1
        self.signature = signature
        self.context_item_id = current_item_id if semantic.get("has_current") else ""
        self.refreshed_at = now
        self.deadline = min(now + FRESHNESS_SECONDS, self.observation_deadline)
        self.expired = False
        wall = self.wall_clock()
        self.value = {'contract_version': VERSION, 'session_id': self.session_id,
                      'revision': self.revision, 'state': 'ready' if sections else 'limited',
                      'issued_at': timestamp(wall), 'valid_until': timestamp(min(wall + FRESHNESS_SECONDS, self.observation_wall_deadline)),
                      'nominal_window_seconds': 900,
                      'supported_window_seconds': 900 if semantic.get('supported') else 0,
                      'current_anchor': {'item_id': self.context_item_id, 'source_url': semantic.get('source_url', '')} if self.context_item_id else None,
                      'summary': summary, 'sections': sections[:3], 'imagery': copy.deepcopy(list(imagery[:2]))}
        return True

    def as_dict(self) -> dict[str, Any]:
        """Expiry projection does not advance revisions/deadlines or do work."""
        result = copy.deepcopy(self.value or {'contract_version': VERSION,
                                             'session_id': self.session_id, 'revision': self.revision,
                                             'state': 'empty', 'nominal_window_seconds': 900,
                                             'supported_window_seconds': 0, 'summary': '',
                                             'sections': [], 'imagery': [], 'current_anchor': None})
        denied = not self.authority()
        if self.withdrawn or denied or (self.value and (self.expired or self.clock() >= self.deadline)):
            result.update(state='withdrawn' if self.withdrawn or denied else 'expired', summary='',
                          supported_window_seconds=0, sections=[], imagery=[], current_anchor=None)
        else:
            # Never send a reference after its earlier asset deadline.
            result['imagery'] = [a for a in result['imagery']
                                 if _valid_wall_deadline(a.get('expires_at'), self.wall_clock())]
        return result

    def invalidate_imagery(self, allowed_urls: set[str]) -> bool:
        """Withdraw pixels without renewing narrative or source deadlines."""
        if not self.value:
            return False
        admitted = [a for a in self.value["imagery"] if a["url"] in allowed_urls]
        if admitted == self.value["imagery"]:
            return False
        self.value["imagery"] = admitted
        self.revision += 1
        self.value["revision"] = self.revision
        return True

    def tick(self) -> bool:
        """Commit one expiry update on an existing observation tick."""
        if not self.authority() and not self.withdrawn:
            return self.withdraw()
        if not self.value or self.expired or self.withdrawn or self.clock() < self.deadline:
            return False
        self.expired = True
        self.revision += 1
        self.value['revision'] = self.revision
        return True

    def withdraw(self) -> bool:
        if self.withdrawn:
            return False
        self.withdrawn = True
        self.revision += 1
        self.value = {**self.as_dict(), 'revision': self.revision}
        return True


def _valid_wall_deadline(value: Any, now: float) -> bool:
    try:
        return type(value) is str and datetime.fromisoformat(value).timestamp() > now
    except (TypeError, ValueError, OverflowError):
        return False
