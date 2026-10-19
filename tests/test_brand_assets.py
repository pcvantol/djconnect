"""Brand identity, HA packaging and source provenance; no optional imaging tools."""

import base64
import hashlib
import json
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "assets/djconnect/brand-v2"
MASTER_SHA = "f05fcdf4602d9c63add7799469c64060a8f13e5efa66ad6c7b762fb8273ec89f"


class BrandAssetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((FAMILY / "manifest.json").read_text())

    def test_exact_approved_source_and_all_packaged_digests(self):
        master = self.manifest["master"]
        self.assertEqual(master["sha256"], MASTER_SHA)
        self.assertEqual(hashlib.sha256((ROOT / master["path"]).read_bytes()).hexdigest(), MASTER_SHA)
        for name, metadata in self.manifest["files"].items():
            with self.subTest(name=name):
                path = ROOT / name
                self.assertFalse(path.is_symlink())
                data = path.read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), metadata["sha256"])
                self.assertEqual(len(data), metadata["bytes"])
                if name.endswith(".png"):
                    self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                    width, height, depth, color = struct.unpack(">IIBB", data[16:26])
                    self.assertEqual((width, height), (metadata["width"], metadata["height"]))
                    self.assertEqual(depth, 8)
                    self.assertEqual(color, 6 if metadata["alpha"] else 2)
        self.assertEqual(hashlib.sha256((ROOT / "scripts/build_brand.py").read_bytes()).hexdigest(),
                         self.manifest["recipe_sha256"])
        font = self.manifest["font"]
        self.assertEqual(hashlib.sha256((ROOT / font["path"]).read_bytes()).hexdigest(), font["sha256"])

    def test_svg_is_self_contained_exact_raster_with_outlined_wordmark(self):
        ns = {"s": "http://www.w3.org/2000/svg"}
        for name in self.manifest["files"]:
            if not name.endswith(".svg"):
                continue
            with self.subTest(name=name):
                svg = ET.fromstring((ROOT / name).read_text())
                images = svg.findall("s:image", ns)
                self.assertEqual(len(images), 1)
                uri = images[0].attrib["href"]
                self.assertTrue(uri.startswith("data:image/png;base64,"))
                raster = "headset-master.png" if name.endswith("/headset.svg") else "glass-master.png"
                self.assertEqual(base64.b64decode(uri.split(",", 1)[1], validate=True), (FAMILY / raster).read_bytes())
                self.assertEqual(svg.findall(".//s:text", ns), [])
                title = svg.find("s:title", ns).text
                if "primary" in name or "djconnect-logo" in name:
                    self.assertEqual(title, "DJConnect — Your music. Your DJ.")
                    self.assertGreater(len(svg.findall(".//s:path", ns)), 9)
                elif "compact" in name:
                    self.assertEqual(title, "DJConnect")
                self.assertIn("not a traced vector icon", svg.find("s:desc", ns).text)

    def test_ha_icons_and_wide_theme_wordmarks_have_distinct_semantics(self):
        for folder in ("brands/djconnect", "brands/custom_integrations/djconnect",
                       "custom_components/djconnect", "custom_components/djconnect/brand"):
            for size, suffix in ((256, ""), (512, "@2x")):
                icon = (ROOT / folder / f"icon{suffix}.png").read_bytes()
                self.assertEqual(icon, (FAMILY / f"mark-{size}.png").read_bytes())
                for prefix in ("", "dark_"):
                    logo = self.manifest["files"][f"{folder}/{prefix}logo{suffix}.png"]
                    self.assertEqual((logo["width"], logo["height"]), (size * 4, size))
                    self.assertTrue(logo["alpha"])
                self.assertNotEqual((ROOT / folder / f"logo{suffix}.png").read_bytes(),
                                    (ROOT / folder / f"dark_logo{suffix}.png").read_bytes())
        for size in (16, 20, 24, 32, 40, 64, 128, 256, 512, 1024):
            record = self.manifest["files"][f"assets/djconnect/brand-v2/mark-{size}.png"]
            self.assertTrue(record["alpha"])
            self.assertEqual(record["role"], "headset-only" if size <= 40 else "glass-mark")
        contour = self.manifest["alpha_contours"]
        self.assertEqual(hashlib.sha256((ROOT / contour["path"]).read_bytes()).hexdigest(), contour["sha256"])
        self.assertFalse(contour["source_rgb_modified"])

    def test_active_brand_paths_do_not_refer_to_legacy_source(self):
        self.assertEqual(self.manifest["tagline_en"], "Your music. Your DJ.")
        for name in ("README.md", "info.md", "assets/djconnect/djconnect-logo.svg"):
            text = (ROOT / name).read_text()
            self.assertNotIn("YOUR PERSONAL AI DJ FOR HOME ASSISTANT", text)
            self.assertNotIn("Muziekbediening met karakter", text)
        # The unreferenced historical image is deliberately not a current brand alias.
        self.assertNotIn("screenshots/djconnect_icon_1024.png", self.manifest["files"])


if __name__ == "__main__":
    unittest.main()
