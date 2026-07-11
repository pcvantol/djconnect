"""Verification execution environment support."""

from .cleanup import CleanupManager, CleanupTarget
from .dependencies import DependencyInspector
from .github import GitHubInspector
from .identity import RunIdentityManager
from .platforms import (
    AppleDevelopmentEnvironment,
    CommandRunner,
    ESP32Environment,
    HomeAssistantEnvironment,
    RaspberryPiEnvironment,
    WindowsDevelopmentEnvironment,
)
from .snapshot import EnvironmentSnapshotter
from .toolchain import ToolchainInspector


def __getattr__(name: str):
    if name == "VerificationExecutionEnvironment":
        from .execution import VerificationExecutionEnvironment

        return VerificationExecutionEnvironment
    raise AttributeError(name)

__all__ = [
    "AppleDevelopmentEnvironment",
    "CleanupManager",
    "CleanupTarget",
    "CommandRunner",
    "DependencyInspector",
    "ESP32Environment",
    "GitHubInspector",
    "HomeAssistantEnvironment",
    "RaspberryPiEnvironment",
    "RunIdentityManager",
    "ToolchainInspector",
    "VerificationExecutionEnvironment",
    "EnvironmentSnapshotter",
    "WindowsDevelopmentEnvironment",
]
