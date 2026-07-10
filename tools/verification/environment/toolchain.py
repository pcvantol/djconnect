"""Platform-neutral toolchain discovery."""

from __future__ import annotations

import platform
import shutil
import subprocess

from tools.verification.models import ResourceState, ToolchainInfo


DEFAULT_TOOLS = (
    ("python", ("python3", "--version")),
    ("git", ("git", "--version")),
    ("node", ("node", "--version")),
    ("npm", ("npm", "--version")),
    ("xcodebuild", ("xcodebuild", "-version")),
    ("swift", ("swift", "--version")),
    ("dotnet", ("dotnet", "--version")),
    ("msbuild", ("msbuild", "-version")),
    ("platformio", ("pio", "--version")),
    ("espidf", ("idf.py", "--version")),
    ("docker", ("docker", "--version")),
    ("prlctl", ("prlctl", "--version")),
)


class ToolchainInspector:
    def discover(self, tools: tuple[tuple[str, tuple[str, ...]], ...] = DEFAULT_TOOLS) -> dict[str, ToolchainInfo]:
        discovered = {
            name: self.inspect(name, command)
            for name, command in tools
        }
        discovered["operating_system"] = ToolchainInfo(
            "operating_system",
            None,
            f"{platform.system()} {platform.release()}",
            ResourceState.AVAILABLE,
        )
        discovered["architecture"] = ToolchainInfo(
            "architecture",
            None,
            platform.machine(),
            ResourceState.AVAILABLE,
        )
        return discovered

    def inspect(self, name: str, command: tuple[str, ...]) -> ToolchainInfo:
        executable = shutil.which(command[0])
        if executable is None:
            return ToolchainInfo(name, None, None, ResourceState.MISSING)
        version = _run_version(command)
        return ToolchainInfo(name, executable, version, ResourceState.AVAILABLE)


def _run_version(command: tuple[str, ...]) -> str | None:
    try:
        return subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).strip().splitlines()[0]
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, IndexError):
        return None
