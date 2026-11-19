"""Runtime channel selection for stable and future/beta verification."""

from __future__ import annotations

import os

STABLE_MODE = "stable"
FUTURE_BETA_MODE = "future_beta"


def verification_test_mode() -> str:
    value = os.getenv("DJCONNECT_VERIFICATION_TEST_MODE", STABLE_MODE).strip().lower()
    return value or STABLE_MODE


def future_beta_enabled() -> bool:
    return verification_test_mode() == FUTURE_BETA_MODE


def beta_channel_allowed(channel: str) -> bool:
    return channel != "beta" or future_beta_enabled()
