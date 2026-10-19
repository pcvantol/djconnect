"""Transparent brand extraction preserves the approved RGB, without a rectangle."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HAS_BUILD_TOOLS = all(importlib.util.find_spec(name) is not None for name in ("PIL", "fontTools"))


@unittest.skipUnless(HAS_BUILD_TOOLS, "Build-only branding tools; enforced by Brand asset reproducibility CI")
class BrandGeneratorTest(unittest.TestCase):
    def test_alpha_sources_preserve_every_original_rgb_pixel_and_fit_silhouette(self):
        from PIL import Image, ImageChops

        family = ROOT / "assets/djconnect/brand-v2"
        original = Image.open(family / "source/DJConnect-BrandV2-APPROVED-ORIGINAL-1254.png")
        contours = json.loads((ROOT / "tools/branding/contours.json").read_text())
        for name in ("glass", "headset"):
            derived = Image.open(family / f"{name}-master.png")
            box = contours[name]["crop"]
            width, height = box[2] - box[0], box[3] - box[1]
            x, y = (derived.width - width) // 2, (derived.height - height) // 2
            self.assertIsNone(ImageChops.difference(
                derived.crop((x, y, x + width, y + height)).convert("RGB"),
                original.crop(box),
            ).getbbox(), name)
            self.assertEqual(derived.mode, "RGBA")
            alpha = derived.getchannel("A")
            self.assertEqual(alpha.getextrema(), (0, 255))
            for corner in ((0, 0), (0, derived.height-1), (derived.width-1, 0), (derived.width-1, derived.height-1)):
                self.assertEqual(alpha.getpixel(corner), 0, name)
            bounds = alpha.getbbox()
            self.assertGreater(max(bounds[2]-bounds[0], bounds[3]-bounds[1]) / derived.width, .97)

    def test_micro_variant_removes_button_and_all_mark_sizes_have_real_transparency(self):
        from PIL import Image

        family = ROOT / "assets/djconnect/brand-v2"
        for size in (16, 20, 24, 32, 40, 64, 128, 256, 512, 1024):
            mark = Image.open(family / f"mark-{size}.png")
            self.assertEqual(mark.mode, "RGBA")
            self.assertEqual(mark.getpixel((0, 0))[3], 0)
            # The full button fills its top edge; the micro headset keeps transparent
            # space above its natural wide silhouette, rather than retaining the button.
            if size <= 40:
                self.assertLessEqual(mark.getpixel((size//2, 0))[3], 3)


if __name__ == "__main__":
    unittest.main()
