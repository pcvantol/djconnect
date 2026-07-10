"""Environment controllers for platform runtimes without verification logic."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tools.verification.models import ManagedPlatform, ResourceState


class CommandRunner:
    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        try:
            output = subprocess.check_output(
                command,
                cwd=cwd,
                text=True,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
            return 0, output.strip()
        except subprocess.CalledProcessError as exc:
            return exc.returncode, str(exc.output).strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)


class HomeAssistantEnvironment:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def discover(self) -> ManagedPlatform:
        executable = shutil.which("ha") or shutil.which("hass")
        return ManagedPlatform(
            "home_assistant",
            ResourceState.AVAILABLE if executable else ResourceState.MISSING,
            {"executable": executable},
        )

    def health(self, base_url: str | None = None) -> ManagedPlatform:
        return ManagedPlatform("home_assistant", ResourceState.UNKNOWN, {"base_url": base_url, "adapter_logic": False})

    def start(self) -> ManagedPlatform:
        return ManagedPlatform("home_assistant", ResourceState.SKIPPED, {"operation": "start", "requires_local_config": True})

    def stop(self) -> ManagedPlatform:
        return ManagedPlatform("home_assistant", ResourceState.SKIPPED, {"operation": "stop", "requires_local_config": True})

    def restart(self) -> ManagedPlatform:
        return ManagedPlatform("home_assistant", ResourceState.SKIPPED, {"operation": "restart", "requires_local_config": True})


class AppleDevelopmentEnvironment:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def discover(self) -> ManagedPlatform:
        xcode = shutil.which("xcodebuild")
        simctl = shutil.which("xcrun")
        return ManagedPlatform(
            "apple_development",
            ResourceState.AVAILABLE if xcode and simctl else ResourceState.MISSING,
            {"xcodebuild": xcode, "xcrun": simctl},
        )

    def simulators(self) -> ManagedPlatform:
        code, output = self.runner.run(("xcrun", "simctl", "list", "devices", "available"), timeout=20)
        return ManagedPlatform(
            "apple_simulators",
            ResourceState.AVAILABLE if code == 0 else ResourceState.MISSING,
            {"output": output[:4000]},
        )


class WindowsDevelopmentEnvironment:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def discover(self) -> ManagedPlatform:
        prlctl = shutil.which("prlctl")
        return ManagedPlatform(
            "windows_development",
            ResourceState.AVAILABLE if prlctl else ResourceState.MISSING,
            {"parallels": prlctl},
        )


class RaspberryPiEnvironment:
    def discover(self, host: str | None = None) -> ManagedPlatform:
        return ManagedPlatform(
            "raspberry_pi",
            ResourceState.UNKNOWN if host else ResourceState.SKIPPED,
            {"host": host, "ssh_available": bool(shutil.which("ssh"))},
        )


class ESP32Environment:
    def discover(self) -> ManagedPlatform:
        pio = shutil.which("pio")
        return ManagedPlatform(
            "esp32",
            ResourceState.AVAILABLE if pio else ResourceState.MISSING,
            {"platformio": pio, "serial_discovery": "externalized"},
        )
