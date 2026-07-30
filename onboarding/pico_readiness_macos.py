#!/usr/bin/env python3
"""Read-only macOS readiness report for DJConnect Pico 2 W development."""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_EXTENSIONS = ("paulober.pico-w-go", "ms-python.python")
PYLANCE_EXTENSIONS = ("ms-python.vscode-pylance", "anysphere.cursorpyright")
DEFAULT_TOOL_VENV = Path.home() / "Library" / "Application Support" / "DJConnect" / "pico-tools"


@dataclass(frozen=True)
class Check:
    state: str
    name: str
    detail: str


def command_version(command: str, *version_args: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    result = subprocess.run([command, *(version_args or ("--version",))], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else executable


def tool_path(venv: Path, name: str) -> Path | None:
    candidate = venv / "bin" / name
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    found = shutil.which(name)
    return Path(found) if found else None


def tool_version(path: Path) -> str:
    result = subprocess.run([str(path), "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else str(path)


def check_extensions() -> list[Check]:
    if not shutil.which("code"):
        return [Check("FAIL", "vscode.extensions", "VS Code command-line launcher 'code' is unavailable.")]
    result = subprocess.run(["code", "--list-extensions"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        return [Check("FAIL", "vscode.extensions", "Could not list VS Code extensions; start VS Code once and enable the 'code' launcher.")]
    installed = {line.strip().lower() for line in result.stdout.splitlines()}
    missing = [extension for extension in REQUIRED_EXTENSIONS if extension not in installed]
    if not any(extension in installed for extension in PYLANCE_EXTENSIONS):
        missing.append("ms-python.vscode-pylance (or anysphere.cursorpyright for Cursor)")
    if missing:
        return [Check("FAIL", "vscode.extensions", f"Missing required extension(s): {', '.join(missing)}.")]
    return [Check("PASS", "vscode.extensions", "MicroPico, Python and Pylance-compatible extensions are installed.")]


def pico_usb_checks() -> list[Check]:
    serial_ports = sorted(Path("/dev").glob("cu.usb*"))
    usb = subprocess.run(["system_profiler", "SPUSBDataType"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    visible = bool(re.search(r"Raspberry|Pico|RP2", usb.stdout, re.IGNORECASE))
    checks = [
        Check("PASS" if visible else "WARNING", "pico.usb", "Pico/RP2 USB device is visible." if visible else "No Pico/RP2 USB device is visible; connect the board with a data-capable USB cable."),
        Check("PASS" if serial_ports else "WARNING", "pico.serial", f"Serial port(s): {', '.join(str(port) for port in serial_ports)}." if serial_ports else "No /dev/cu.usb* serial port is available; firmware or the USB cable may be the cause."),
    ]
    return checks


def firmware_check(mpremote: Path | None) -> Check:
    if not mpremote:
        return Check("WARNING", "pico.firmware", "Firmware cannot be queried until mpremote is installed.")
    result = subprocess.run([str(mpremote), "connect", "auto", "exec", "import sys; print(sys.implementation)"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        return Check("WARNING", "pico.firmware", "No responding MicroPython Pico was detected. Flash the current stable RPI_PICO2_W UF2 before first use.")
    return Check("PASS", "pico.firmware", f"MicroPython reports: {result.stdout.strip()[:160]}")


def evaluate(venv: Path) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check("PASS" if platform.system() == "Darwin" else "FAIL", "host.macos", f"{platform.system()} {platform.machine()}"))
    checks.append(Check("PASS" if shutil.which("brew") else "FAIL", "homebrew", command_version("brew") or "Homebrew is not installed."))
    checks.append(Check("PASS" if sys.version_info >= (3, 12) else "FAIL", "python", platform.python_version()))
    checks.append(Check("PASS" if shutil.which("git") else "FAIL", "git", command_version("git") or "Git is not installed."))
    checks.append(Check("PASS" if shutil.which("code") else "FAIL", "vscode", command_version("code") or "Install VS Code and add its 'code' command to PATH."))
    checks.extend(check_extensions())
    for name in ("mpremote", "stubber", "ruff"):
        path = tool_path(venv, name)
        checks.append(Check("PASS" if path else "FAIL", f"micropython.{name}", tool_version(path) if path else f"Missing {name}; run onboarding Pico tooling step."))
    picotool = command_version("picotool", "version")
    checks.append(Check("PASS" if picotool else "FAIL", "picotool", picotool or "Missing picotool; run onboarding Pico tooling step."))
    venv_bin = str(venv / "bin")
    checks.append(Check("PASS" if venv_bin in os.environ.get("PATH", "").split(os.pathsep) else "WARNING", "path.pico_tools", f"{venv_bin} is on PATH." if venv_bin in os.environ.get("PATH", "").split(os.pathsep) else f"{venv_bin} is not on PATH; onboarding uses the isolated tools directly and does not modify shell configuration."))
    checks.extend(pico_usb_checks())
    checks.append(firmware_check(tool_path(venv, "mpremote")))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-venv", type=Path, default=DEFAULT_TOOL_VENV)
    args = parser.parse_args()
    checks = evaluate(args.tool_venv)
    print("# DJConnect Pico 2 W Development Readiness")
    print("| State | Check | Detail |")
    print("| --- | --- | --- |")
    for check in checks:
        print(f"| {check.state} | {check.name} | {check.detail.replace('|', '/')} |")
    failed = [check for check in checks if check.state == "FAIL"]
    warnings = [check for check in checks if check.state == "WARNING"]
    verdict = "FAIL" if failed else "WARNING" if warnings else "PASS"
    print(f"\nVerdict: **{verdict}** ({len(failed)} fail, {len(warnings)} warning).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
