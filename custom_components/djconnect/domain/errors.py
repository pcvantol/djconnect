"""Canonical DJConnect domain errors."""

from __future__ import annotations


class DJConnectDomainError(Exception):
    """Base class for core DJConnect domain errors."""


class ResolverError(DJConnectDomainError):
    """Base class for profile resolver failures."""


class ProfileNotFound(ResolverError):
    """Raised when a referenced profile does not exist."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Profile not found: {profile_id}")


class ProfileRequired(ResolverError):
    """Raised when no profile can be resolved."""

    def __init__(self) -> None:
        super().__init__("A DJConnect Profile is required for this request.")


class DeviceNotMapped(ResolverError):
    """Raised when a device exists but has no linked profile."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        super().__init__(f"Device is not mapped to a profile: {device_id}")


class UnknownBackend(DJConnectDomainError):
    """Raised when a music backend registration is unknown."""

    def __init__(self, backend_id: str) -> None:
        self.backend_id = backend_id
        super().__init__(f"Unknown music backend: {backend_id}")


class UnknownMusicAccount(DJConnectDomainError):
    """Raised when a music account registration is unknown."""

    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        super().__init__(f"Unknown music account: {account_id}")
