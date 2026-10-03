"""Guard the DJConnect boundary after retiring the embedded EP runtime."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_ROOTS = (
    ROOT / ".github" / "workflows",
    ROOT / "custom_components",
    ROOT / "onboarding",
    ROOT / "scripts",
    ROOT / "tests",
    ROOT / "tools",
)
SOURCE_SUFFIXES = {".py", ".sh", ".ps1", ".yml", ".yaml", ".json", ".toml", ".js", ".mjs"}
OLD_MODULE = ".".join(("tools", "engineering"))
OLD_PATH = "/".join(("tools", "engineering"))
HISTORICAL_ASSERTIONS = ROOT / "onboarding" / "tests" / "test_onboarding_scripts.py"


def active_sources():
    for directory in ACTIVE_ROOTS:
        if directory.is_dir():
            yield from (path for path in directory.rglob("*") if path.suffix in SOURCE_SUFFIXES)


class EPSourceRetirementTests(unittest.TestCase):
    def test_embedded_runtime_and_exclusive_tests_are_absent(self) -> None:
        self.assertFalse((ROOT / "tools" / "engineering").exists())
        self.assertFalse((ROOT / "tests" / "engineering").exists())

    def test_active_entrypoints_do_not_reach_retired_source(self) -> None:
        failures = []
        for path in active_sources():
            source = path.read_text(encoding="utf-8")
            for line in source.splitlines():
                if OLD_MODULE not in line and OLD_PATH not in line:
                    continue
                historical_assertion = (
                    path == HISTORICAL_ASSERTIONS
                    and line.strip().startswith("for legacy in (")
                    and line.strip().endswith("):")
                )
                if not historical_assertion:
                    failures.append(str(path.relative_to(ROOT)))
            if path.suffix == ".py":
                tree = ast.parse(source, filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = (alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        names = (node.module or "",)
                    else:
                        continue
                    if any(name == OLD_MODULE or name.startswith(OLD_MODULE + ".") for name in names):
                        failures.append(str(path.relative_to(ROOT)))
        self.assertEqual([], sorted(set(failures)))

    def test_standalone_release_is_exact_and_traceable(self) -> None:
        pin = json.loads((ROOT / ".engineering-platform" / "release-pin.json").read_text())
        requirement_lines = [
            line.strip()
            for line in (ROOT / ".engineering-platform" / "requirements.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertEqual(pin["project_id"], "djconnect")
        self.assertEqual(pin["distribution"], "engineering-platform")
        self.assertRegex(pin["version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(pin["wheel_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(pin["source_revision"], r"^[0-9a-f]{40}$")
        self.assertEqual(pin["wheel"], f"engineering_platform-{pin['version']}-py3-none-any.whl")
        self.assertEqual(pin["release_tag"], f"engineering-platform-v{pin['version']}")
        self.assertEqual(pin["supported_boundary"], "installed_cli_or_server_http_json")
        self.assertEqual(pin["legacy_local_consumer_api"], "unsupported")
        self.assertEqual(
            requirement_lines,
            [f"engineering-platform=={pin['version']} --hash=sha256:{pin['wheel_sha256']}"],
        )
        self.assertTrue(pin["release_receipt"].startswith("https://github.com/pcvantol/engineering-platform/releases/download/"))

    def test_historical_evidence_and_project_identity_remain(self) -> None:
        self.assertTrue((ROOT / "docs" / "engineering" / "extraction" / "EP_2X_EXTRACTION_MANIFEST.json").is_file())
        self.assertTrue((ROOT / "docs" / "adr" / "0026-ep-clean-slate-standalone-store-and-migration-retirement.md").is_file())
        repository = json.loads((ROOT / ".engineering-platform" / "repository.json").read_text())
        self.assertEqual(repository["project"]["id"], "djconnect")
        self.assertEqual(repository["repository"]["id"], "djconnect")


if __name__ == "__main__":
    unittest.main()
