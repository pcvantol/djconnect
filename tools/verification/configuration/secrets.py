"""Secret discovery without persisting secret values."""

from __future__ import annotations

import json
import os
from pathlib import Path

from tools.verification.models import SecretBundle


class SecretLoader:
    def load(self, secrets_file: Path | None = None) -> SecretBundle:
        names: set[str] = set()
        source = "environment"
        for key in os.environ:
            if key.startswith("DJCONNECT_VERIFICATION_SECRET_"):
                names.add(key.removeprefix("DJCONNECT_VERIFICATION_SECRET_").lower())
        if secrets_file is not None and secrets_file.exists():
            source = str(secrets_file)
            value = json.loads(secrets_file.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                names.update(str(key) for key in value)
        return SecretBundle(names=tuple(sorted(names)), source=source)
