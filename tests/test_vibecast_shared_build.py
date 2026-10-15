"""Shared renderer artifact behavior, before the production refactor."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SharedVibeCastBuildTest(unittest.TestCase):
    def test_two_hosts_share_renderer_and_build_is_reproducible(self):
        path = ROOT / "scripts/build_vibecast.py"
        self.assertTrue(path.is_file(), "Missing shared local/static renderer build")
        spec = importlib.util.spec_from_file_location("build_vibecast", path)
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            build.build(ROOT, Path(one), source_revision="a" * 40)
            build.build(ROOT, Path(two), source_revision="a" * 40)
            self.assertEqual(build.verify(Path(one)), [])
            self.assertEqual(
                (Path(one) / "manifest.json").read_bytes(),
                (Path(two) / "manifest.json").read_bytes(),
            )
            local = (Path(one) / "local/vibecast.html").read_text()
            static = (Path(one) / "cast/index.html").read_text()
            core = (ROOT / "custom_components/djconnect/vibecast_renderer/renderer.js").read_text()
            self.assertIn(core, local)
            self.assertIn(core, static)
            self.assertNotIn("gstatic.com", local)
            self.assertIn("addCustomMessageListener", static)
            self.assertNotIn("getCastMessageBus", static)
            (Path(one) / "cast/index.html").write_text("wrong asset")
            self.assertTrue(build.verify(Path(one)))

    def test_committed_local_build_cannot_drift_from_source(self):
        import runpy

        build = runpy.run_path(str(ROOT / "scripts/build_vibecast.py"))
        self.assertEqual(
            (ROOT / "custom_components/djconnect/vibecast.html").read_text(),
            build["render"](ROOT, "local"),
        )

    def test_missing_assets_and_source_changes_affect_both_builds(self):
        import runpy
        import shutil

        build = runpy.run_path(str(ROOT / "scripts/build_vibecast.py"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            shutil.copytree(
                ROOT / "custom_components/djconnect/vibecast_renderer",
                root / "custom_components/djconnect/vibecast_renderer",
            )
            one = Path(temp) / "one"
            two = Path(temp) / "two"
            build["build"](root, one, source_revision="a" * 40)
            p = root / "custom_components/djconnect/vibecast_renderer/renderer.js"
            p.write_text(p.read_text() + "\n/* source-change */\n")
            build["build"](root, two, source_revision="b" * 40)
            for name in ["local/vibecast.html", "cast/index.html"]:
                self.assertNotEqual((one / name).read_bytes(), (two / name).read_bytes())
            (two / "cast/index.html").unlink()
            self.assertIn("missing_or_changed_asset:cast/index.html", build["verify"](two))

    def test_host_scripts_use_legacy_syntax_and_no_private_storage(self):
        folder = ROOT / "custom_components/djconnect/vibecast_renderer"
        for name in ["renderer.js", "local-host.js", "cast-host.js"]:
            source = (folder / name).read_text()
            for forbidden in [
                "?.",
                ".at(",
                ".replaceAll(",
                "localStorage",
                "sessionStorage",
                "/session/history",
                "/ask_dj",
            ]:
                self.assertNotIn(forbidden, source)

    def test_manifest_metadata_and_pin_cannot_be_rewritten(self):
        import copy
        import json
        import runpy

        build = runpy.run_path(str(ROOT / "scripts/build_vibecast.py"))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            manifest = build["build"](ROOT, output, source_revision="a" * 40)
            raw = (output / "manifest.json").read_bytes()
            trusted = build["digest"](raw)
            for field, value in [
                ("renderer_source_sha256", "0" * 64),
                ("source_revision", "invented-source"),
                ("contracts", {"required_capabilities": {"owner_controls": True}}),
                ("sources", {"renderer.js": "not-a-hash"}),
            ]:
                changed = copy.deepcopy(manifest)
                changed[field] = value
                (output / "manifest.json").write_text(json.dumps(changed))
                self.assertTrue(build["verify"](output), field)
                self.assertIn(
                    "untrusted_manifest_digest",
                    build["verify"](output, expected_manifest_sha256=trusted),
                )
            (output / "manifest.json").write_bytes(raw)
            self.assertEqual(
                build["verify"](
                    output, expected_manifest_sha256=trusted, expected_revision="a" * 40
                ),
                [],
            )
            self.assertIn(
                "wrong_source_revision", build["verify"](output, expected_revision="b" * 40)
            )
            asset = output / "cast/index.html"
            saved = output / "other.html"
            saved.write_bytes(asset.read_bytes())
            asset.unlink()
            asset.symlink_to(saved)
            self.assertIn("missing_or_changed_asset:cast/index.html", build["verify"](output))

    def test_generated_script_parser_accepts_html_tag_case_and_external_sdk(self):
        import runpy

        build = runpy.run_path(str(ROOT / "scripts/build_vibecast.py"))
        parser = build["InlineScripts"]()
        parser.feed(
            '<SCRIPT SRC="https://sdk.test/x.js"></SCRIPT><SCRIPT>const text="<not-a-tag>";</SCRIPT>'
        )
        self.assertEqual(parser.scripts, ['const text="<not-a-tag>";'])
