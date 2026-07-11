"""Apple Xcode and iOS simulator runtime maintenance helpers."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.verification.apple_runtime_qualification import latest_ios_simulator_runtime
from tools.verification.evidence import RunStore
from tools.verification.environment.identity import RunIdentityManager
from tools.verification.environment.platforms import CommandRunner


@dataclass(frozen=True)
class AppleToolchainEnsureResult:
    run_id: str
    state: str
    started_at: float
    completed_at: float
    xcode_version: str | None
    software_update: dict[str, Any]
    ios_platform_update: dict[str, Any]
    latest_ios_runtime: dict[str, Any] | None
    evidence_dir: str


class AppleToolchainMaintenance:
    """Keep Apple verification tooling current without hiding operator gates."""

    def __init__(self, root: Path, *, runner: CommandRunner | None = None) -> None:
        self.root = root
        self.runner = runner or CommandRunner()
        self.evidence_root = root / "artifacts" / "verification" / "evidence"

    def ensure_ios_runtime(self) -> AppleToolchainEnsureResult:
        started = time.time()
        run_id = RunIdentityManager().create([], prefix="appletoolchain").run_id
        store = RunStore(self.evidence_root)
        run_dir = store.ensure(run_id)

        xcode_code, xcode_output = self.runner.run(("xcodebuild", "-version"), timeout=10)
        software_update = _software_update_list(self.runner)
        ios_platform_update = self._download_ios_platform()
        latest_runtime = latest_ios_simulator_runtime(self.runner)
        state = "PASS" if xcode_code == 0 and ios_platform_update.get("ok") and latest_runtime else "BLOCKED"

        result = AppleToolchainEnsureResult(
            run_id=run_id,
            state=state,
            started_at=started,
            completed_at=time.time(),
            xcode_version=xcode_output if xcode_code == 0 else None,
            software_update=software_update,
            ios_platform_update=ios_platform_update,
            latest_ios_runtime=latest_runtime,
            evidence_dir=str(run_dir),
        )
        store.write_json(run_id, "apple/toolchain-ensure-ios-runtime.json", asdict(result))
        store.finalize(
            run_id,
            state=state,
            summary={
                "phase": "apple_toolchain",
                "gate": "ensure_ios_runtime",
                "xcode_update_available": software_update.get("xcode_update_available"),
                "latest_ios_runtime": latest_runtime,
            },
        )
        return result

    def _download_ios_platform(self) -> dict[str, Any]:
        code, output = self.runner.run(("xcodebuild", "-downloadPlatform", "iOS"), timeout=3600)
        return {
            "ok": code == 0,
            "returncode": code,
            "command": ["xcodebuild", "-downloadPlatform", "iOS"],
            "output_tail": output[-4000:],
        }


def _software_update_list(runner: CommandRunner) -> dict[str, Any]:
    code, output = runner.run(("softwareupdate", "--list"), timeout=120)
    lowered = output.lower()
    return {
        "ok": code == 0,
        "returncode": code,
        "xcode_update_available": "xcode" in lowered,
        "output_excerpt": output[:4000],
        "note": "Mac App Store Xcode updates may require operator approval even when Software Update reports none.",
    }


def result_to_json(result: AppleToolchainEnsureResult) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True)
