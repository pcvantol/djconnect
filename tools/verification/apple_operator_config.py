"""Prepare operator-owned Apple qualification configuration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.verification.apple_runtime_qualification import (
    _distribution_signing_required,
    _extract_xcode_signing_settings,
    _find_distribution_profile,
    _redacted_output_tail,
    latest_ios_simulator_runtime,
)
from tools.verification.environment.platforms import CommandRunner


@dataclass(frozen=True)
class AppleQualificationConfigResult:
    state: str
    exports: dict[str, str]
    target: dict[str, Any] | None
    latest_ios_runtime: dict[str, Any] | None
    checks: tuple[dict[str, Any], ...]
    followups_resolved: tuple[str, ...]
    followups_blocked: tuple[str, ...]


class AppleQualificationConfigPreparer:
    """Build the non-secret env bundle needed by Phase 10E-R2."""

    def __init__(
        self,
        root: Path,
        *,
        apple_repo: Path | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self.root = root
        self.apple_repo = apple_repo or root.parent / "djconnect-app"
        self.runner = runner or CommandRunner()

    def prepare(self) -> AppleQualificationConfigResult:
        checks: list[dict[str, Any]] = []
        exports: dict[str, str] = {}

        runtime = latest_ios_simulator_runtime(self.runner)
        target = self._target_for_runtime(runtime)
        if target is None:
            checks.append(_check("latest_stable_target", "BLOCKED", "No latest-stable iOS simulator target is available.", {"latest_ios_runtime": runtime}))
        else:
            target_json = json.dumps(target, sort_keys=True, separators=(",", ":"))
            exports["DJCONNECT_VERIFICATION_APPLE_TARGET_JSON"] = target_json
            checks.append(_check("latest_stable_target", "PASS", "Prepared target JSON resolves to the latest eligible stable iOS simulator runtime.", {"target": target, "latest_ios_runtime": runtime}))

        derived_data = str((self.root / "artifacts" / "verification" / "apple" / "DerivedData").resolve())
        exports["DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA"] = derived_data
        checks.append(_check("derived_data", "PASS", "Prepared DerivedData path is under artifacts/verification and can be cleaned by the runtime gate.", {"derived_data": derived_data}))

        release_product = f"{derived_data}/Build/Products/Release-iphonesimulator/DJConnect.app"
        exports["DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND"] = (
            "xcodebuild -project DJConnectApp.xcodeproj -scheme DJConnectIOS "
            "-configuration Release -destination 'generic/platform=iOS Simulator' "
            f"-derivedDataPath {derived_data} CODE_SIGNING_ALLOWED=NO clean build"
        )
        exports["DJCONNECT_VERIFICATION_APPLE_UI_DRIVER"] = "xctest"
        if target:
            exports["DJCONNECT_VERIFICATION_APPLE_TARGET_UDID"] = str(target["udid"])
            destination = f"platform=iOS Simulator,id={target['udid']}"
        else:
            destination = "platform=iOS Simulator,id=${DJCONNECT_VERIFICATION_APPLE_TARGET_UDID}"
        exports["DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND"] = (
            "xcodebuild test -project DJConnectApp.xcodeproj -scheme DJConnectIOS "
            f"-destination '{destination}' "
            f"-derivedDataPath {derived_data} -only-testing:DJConnectIOSUITests/DJConnectIOSUITests/testPrimaryTabsAreAvailable"
        )
        checks.append(_check("ui_healthcheck", "PASS", "Prepared XCTest UI healthcheck command for the selected simulator target.", {"driver": "xctest"}))

        xcode_account = self._xcode_account_check()
        checks.append(xcode_account)
        bundle_id = _bundle_id_from_xcode_account(xcode_account)
        if target is not None and bundle_id:
            target = {**target, "bundle_id": bundle_id}
            exports["DJCONNECT_VERIFICATION_APPLE_TARGET_JSON"] = json.dumps(target, sort_keys=True, separators=(",", ":"))
        signing = self._signing_check()
        checks.append(signing)
        if xcode_account["state"] == "PASS" and signing["state"] == "PASS":
            for key in (
                "DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY",
                "DJCONNECT_VERIFICATION_APPLE_TEAM_ID",
                "DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID",
                "DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE",
            ):
                exports[key] = os.getenv(key, "")

        followups_resolved = ["VPB-031"]
        followups_blocked: list[str] = []
        if target is not None:
            followups_resolved.append("VPB-036")
        else:
            followups_blocked.append("VPB-036")
        if xcode_account["state"] == "PASS" and signing["state"] in {"PASS", "SKIPPED"}:
            followups_resolved.append("VPB-037")
        else:
            followups_blocked.append("VPB-037")
        followups_resolved.append("VPB-038")

        state = "READY" if not followups_blocked else "BLOCKED"
        return AppleQualificationConfigResult(
            state=state,
            exports=exports,
            target=target,
            latest_ios_runtime=runtime,
            checks=tuple(checks),
            followups_resolved=tuple(followups_resolved),
            followups_blocked=tuple(followups_blocked),
        )

    def _target_for_runtime(self, runtime: dict[str, Any] | None) -> dict[str, Any] | None:
        if not runtime:
            return None
        devices = [device for device in runtime.get("devices", []) if isinstance(device, dict) and device.get("udid")]
        if not devices:
            return None
        preferred = sorted(
            devices,
            key=lambda item: (
                0 if str(item.get("state", "")).lower() == "booted" else 1,
                0 if "iphone" in str(item.get("name", "")).lower() else 1,
                str(item.get("name", "")),
            ),
        )[0]
        derived_data = str((self.root / "artifacts" / "verification" / "apple" / "DerivedData").resolve())
        return {
            "target_id": "latest-stable-ios-simulator",
            "variant": "ios",
            "runtime": "simulator",
            "name": str(preferred.get("name") or ""),
            "udid": str(preferred["udid"]),
            "bundle_id": os.getenv("DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID", "com.djconnect.app"),
            "app_path": f"{derived_data}/Build/Products/Release-iphonesimulator/DJConnect.app",
            "metadata": {
                "ios_version": runtime.get("version"),
                "runtime_version": runtime.get("version"),
                "runtime_identifier": runtime.get("runtime"),
                "runtime_channel": runtime.get("channel"),
            },
        }

    def _xcode_account_check(self) -> dict[str, Any]:
        project = self.apple_repo / "DJConnectApp.xcodeproj"
        if not self.apple_repo.exists() or not project.exists():
            return _check("xcode_account", "BLOCKED", "Apple source repository or Xcode project is unavailable.", {"apple_repo": str(self.apple_repo)})
        command = (
            "xcodebuild",
            "-project",
            str(project),
            "-scheme",
            os.getenv("DJCONNECT_VERIFICATION_APPLE_SCHEME", "DJConnectIOS"),
            "-showBuildSettings",
            "-json",
            "-allowProvisioningUpdates",
        )
        code, output = self.runner.run(command, cwd=self.apple_repo, timeout=120)
        return _check(
            "xcode_account",
            "PASS" if code == 0 else "BLOCKED",
            "Xcode accepted automatic provisioning access for the Apple project."
            if code == 0
            else "Xcode automatic provisioning is unavailable; sign in to Xcode with an Apple developer account and refresh credentials/profiles.",
            {
                "returncode": code,
                "project": str(project),
                "scheme": command[4],
                "allow_provisioning_updates": True,
                "settings": _extract_xcode_signing_settings(output) if code == 0 else {},
                "output_tail": _redacted_output_tail(output),
            },
        )

    def _signing_check(self) -> dict[str, Any]:
        required = {
            "DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY": os.getenv("DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY", "").strip(),
            "DJCONNECT_VERIFICATION_APPLE_TEAM_ID": os.getenv("DJCONNECT_VERIFICATION_APPLE_TEAM_ID", "").strip(),
            "DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID": os.getenv("DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID", "").strip(),
            "DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE": os.getenv("DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE", "").strip(),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            if not _distribution_signing_required():
                return _check(
                    "distribution_signing_assets",
                    "SKIPPED",
                    "App Store/TestFlight distribution signing is deferred for current platform verification.",
                    {
                        "missing": missing,
                        "required_for_current_run": False,
                        "enable_with": "DJCONNECT_VERIFICATION_APPLE_REQUIRE_DISTRIBUTION_SIGNING=1",
                    },
                )
            return _check("distribution_signing_assets", "BLOCKED", "Distribution signing expectations are not configured.", {"missing": missing})
        code, identities = self.runner.run(("security", "find-identity", "-v", "-p", "codesigning"), timeout=20)
        identity_ok = code == 0 and required["DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY"] in identities and required["DJCONNECT_VERIFICATION_APPLE_TEAM_ID"] in identities
        profile = _find_distribution_profile(
            expected_profile=required["DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE"],
            expected_team_id=required["DJCONNECT_VERIFICATION_APPLE_TEAM_ID"],
            expected_bundle_id=required["DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID"],
            runner=self.runner,
        )
        return _check(
            "distribution_signing_assets",
            "PASS" if identity_ok and profile else "BLOCKED",
            "Distribution signing identity and provisioning profile matched." if identity_ok and profile else "Distribution signing identity or provisioning profile is unavailable.",
            {"identity_found": identity_ok, "profile_found": profile is not None, "matched_profile": profile or {}},
        )


def _check(name: str, state: str, message: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "state": state, "message": message, "data": data}


def _bundle_id_from_xcode_account(check: dict[str, Any]) -> str:
    data = check.get("data")
    if not isinstance(data, dict):
        return ""
    settings = data.get("settings")
    if not isinstance(settings, dict):
        return ""
    for target_settings in settings.values():
        if not isinstance(target_settings, dict):
            continue
        bundle_id = str(target_settings.get("PRODUCT_BUNDLE_IDENTIFIER") or "").strip()
        if bundle_id:
            return bundle_id
    return ""


def result_to_json(result: AppleQualificationConfigResult) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True)
