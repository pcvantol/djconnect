#!/usr/bin/env python3
"""Fail-closed local readiness check for DJConnect Apple internal releases.

The current internal-release flow signs on the qualified MacBook only. This
tool deliberately reports only metadata needed to prove readiness; it never
prints profile contents, private keys, passwords, device identifiers, or
certificate fingerprints.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import plistlib
import subprocess
import sys
from pathlib import Path


REQUIRED_IOS_BUNDLES = (
    "dev.djconnect.ios",
    "dev.djconnect.ios.watch",
    "dev.djconnect.ios.watch.complications",
    "dev.djconnect.ios.track-insight-widget",
)


def command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def profile_matches_bundle(application_identifier: str, team_id: str, bundle_id: str) -> bool:
    expected = f"{team_id}.{bundle_id}"
    return application_identifier == expected or (
        application_identifier.endswith(".*") and expected.startswith(application_identifier[:-1])
    )


def read_profile(path: Path) -> dict | None:
    result = command("security", "cms", "-D", "-i", str(path))
    if result.returncode:
        return None
    try:
        parsed = plistlib.loads(result.stdout.encode())
    except plistlib.InvalidFileException:
        return None
    return parsed if isinstance(parsed, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apple-repo", type=Path, required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--signing-identity", required=True)
    parser.add_argument("--profile-dir", type=Path, action="append", default=[])
    args = parser.parse_args()

    checks: list[dict[str, object]] = []
    project = args.apple_repo / "DJConnectApp.xcodeproj"
    xcode = command(
        "xcodebuild", "-project", str(project), "-scheme", "DJConnectIOS",
        "-showBuildSettings", "-allowProvisioningUpdates",
    )
    checks.append({
        "name": "apple_developer_account",
        "state": "PASS" if xcode.returncode == 0 else "BLOCKED",
        "message": "Xcode accepted Apple Developer provisioning access."
        if xcode.returncode == 0
        else "Sign in to Xcode with the DJConnect Apple Developer account and refresh its profiles.",
    })

    identities = command("security", "find-identity", "-v", "-p", "codesigning")
    identity_found = identities.returncode == 0 and args.signing_identity in identities.stdout and args.team_id in identities.stdout
    checks.append({
        "name": "apple_development_identity",
        "state": "PASS" if identity_found else "BLOCKED",
        "message": "Configured Apple Development identity is available in the login keychain."
        if identity_found else "Configured Apple Development identity is missing from the login keychain.",
    })

    profile_dirs = args.profile_dir or [
        Path("~/Library/Developer/Xcode/UserData/Provisioning Profiles").expanduser(),
        Path("~/Library/MobileDevice/Provisioning Profiles").expanduser(),
    ]
    covered: set[str] = set()
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    for directory in profile_dirs:
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            if path.suffix not in {".mobileprovision", ".provisionprofile"}:
                continue
            profile = read_profile(path)
            if not profile:
                continue
            expiration = profile.get("ExpirationDate")
            if isinstance(expiration, dt.datetime) and expiration.replace(tzinfo=None) <= now:
                continue
            entitlements = profile.get("Entitlements")
            if not isinstance(entitlements, dict) or not entitlements.get("get-task-allow"):
                continue
            teams = profile.get("TeamIdentifier")
            if not isinstance(teams, list) or args.team_id not in teams:
                continue
            app_identifier = str(entitlements.get("application-identifier", ""))
            for bundle_id in REQUIRED_IOS_BUNDLES:
                if profile_matches_bundle(app_identifier, args.team_id, bundle_id):
                    covered.add(bundle_id)

    missing = sorted(set(REQUIRED_IOS_BUNDLES) - covered)
    checks.append({
        "name": "development_provisioning_profiles",
        "state": "PASS" if not missing else "BLOCKED",
        "message": "Valid local development profiles cover all required iPhone and Watch bundles."
        if not missing else "Missing valid local development-profile coverage for one or more required iPhone/Watch bundles.",
        "covered_bundle_ids": sorted(covered),
        "missing_bundle_ids": missing,
    })

    ready = all(check["state"] == "PASS" for check in checks)
    print(json.dumps({"state": "READY" if ready else "BLOCKED", "team_id": args.team_id, "checks": checks}, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
