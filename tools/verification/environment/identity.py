"""Traceable run identity generation for verification executions."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from tools.verification.models import RunIdentity, Scenario


class RunIdentityManager:
    def create(self, scenarios: list[Scenario] | None = None, *, prefix: str = "djv") -> RunIdentity:
        scenario_ids = tuple(scenario.id for scenario in scenarios or ())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        nonce = uuid4().hex[:10]
        run_id = f"{prefix}-{timestamp}-{nonce}"
        payload = "|".join((run_id, *scenario_ids))
        environment_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        correlation_id = uuid4().hex
        return RunIdentity(
            run_id=run_id,
            environment_id=environment_id,
            correlation_id=correlation_id,
            scenario_ids=scenario_ids,
            artifact_prefix=f"{run_id}/",
        )
