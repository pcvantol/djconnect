"""Build Brand V2 from the exact approved raster and licensed outlined typography.

Offline after installing tools/branding/requirements.txt. No AI, system fonts,
network, native asset-catalog edits, release or deployment effects.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import zlib

import fontTools
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageChops, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

ROOT = Path(__file__).resolve().parents[1]
FAMILY = Path("assets/djconnect/brand-v2")
MASTER = FAMILY / "source/DJConnect-BrandV2-APPROVED-ORIGINAL-1254.png"
MASTER_SHA = "f05fcdf4602d9c63add7799469c64060a8f13e5efa66ad6c7b762fb8273ec89f"
FONT = Path("tools/branding/fonts/InterVariable.ttf")
FONT_SHA = "4989b125924991b90d05b2d16e0e388c48f7d5bb8b30539bbf9c755278d0ccaf"
CONTOURS = Path("tools/branding/contours.json")
TAGLINE = "Your music. Your DJ."
HA_FOLDERS = (
    "brands/djconnect", "brands/custom_integrations/djconnect",
    "custom_components/djconnect", "custom_components/djconnect/brand",
)
ICON_SIZES = (16, 20, 24, 32, 40, 64, 128, 256, 512, 1024)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png(image: Image.Image) -> bytes:
    # Pillow's zlib-ng encoder selects architecture-specific compressed streams.
    # Own the PNG framing/filter and use classic zlib with fixed Huffman coding,
    # rather than shipping host-dependent PNG bytes in embedded SVGs/manifests.
    if image.mode not in {"RGB", "RGBA"}:
        raise ValueError("unsupported_brand_image_mode")
    preceding = Image.new(image.mode, image.size)
    preceding.paste(image, (1, 0))
    pixels = ImageChops.subtract_modulo(image, preceding).tobytes()
    stride = image.width * len(image.getbands())
    filtered = b"".join(b"\x01" + pixels[offset:offset + stride]
                        for offset in range(0, len(pixels), stride))
    encoder = zlib.compressobj(level=9, wbits=15, memLevel=8, strategy=zlib.Z_FIXED)
    compressed = encoder.compress(filtered) + encoder.flush()

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", image.width, image.height, 8,
                         6 if image.mode == "RGBA" else 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


class AlphaContour(BasePen):
    """Rasterize editable SVG alpha contours; never redraw source RGB artwork."""

    def __init__(self, draw):
        super().__init__(None)
        self.draw = draw
        self.points = []

    def _moveTo(self, point):
        self.points = [point]

    def _lineTo(self, point):
        self.points.append(point)

    def _curveToOne(self, one, two, end):
        start = self.points[-1]
        for step in range(1, 97):
            t = step / 96
            self.points.append(tuple(
                (1-t)**3 * start[i] + 3*(1-t)**2*t*one[i]
                + 3*(1-t)*t*t*two[i] + t**3*end[i] for i in (0, 1)
            ))

    def _closePath(self):
        self.draw.polygon([(round(x * 4), round(y * 4)) for x, y in self.points], fill=255)
        self.points = []


def cutout(image, specification):
    """Apply a source-coordinate alpha boundary, retaining every interior RGB pixel."""
    alpha = Image.new("L", (image.width * 4, image.height * 4))
    pen = AlphaContour(ImageDraw.Draw(alpha))
    for path in specification["paths"]:
        parse_path(path, pen)
    alpha = alpha.resize(image.size, Image.Resampling.LANCZOS)
    rgba = image.convert("RGBA")
    rgba.putalpha(alpha)
    rgba = rgba.crop(specification["crop"])
    side = max(rgba.size)
    canvas = Image.new("RGBA", (side, side))
    # Paste without an alpha mask: preserve straight-alpha source RGB exactly.
    canvas.paste(rgba, ((side - rgba.width) // 2, (side - rgba.height) // 2))
    return canvas


class Typeface:
    """One pinned font instance, identical advances for SVG outlines and PNGs."""

    def __init__(self, data: bytes, weight: int):
        self.font = instantiateVariableFont(
            TTFont(io.BytesIO(data), recalcTimestamp=False),
            {"wght": weight, "opsz": 32}, inplace=True,
        )
        self.font.recalcTimestamp = False
        out = io.BytesIO()
        self.font.save(out)
        self.data = out.getvalue()
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.units = self.font["head"].unitsPerEm

    def layout(self, text, size):
        x = 0.0
        for char in text:
            name = self.cmap[ord(char)]
            yield char, name, x
            x += self.font["hmtx"][name][0] * size / self.units

    def svg(self, text, size, x, baseline, color):
        paths = []
        scale = size / self.units
        for _, name, advance in self.layout(text, size):
            pen = SVGPathPen(self.glyphs)
            self.glyphs[name].draw(pen)
            paths.append(
                f'<path transform="translate({x + advance:.6f} {baseline}) '
                f'scale({scale:.9f} {-scale:.9f})" d="{pen.getCommands()}"/>'
            )
        return f'<g fill="{color}">' + "".join(paths) + "</g>"

    def draw(self, image, text, size, x, baseline, color):
        font = ImageFont.truetype(io.BytesIO(self.data), size=size,
                                  layout_engine=ImageFont.Layout.BASIC)
        draw = ImageDraw.Draw(image)
        for char, _, advance in self.layout(text, size):
            draw.text((x + advance, baseline), char, font=font, fill=color, anchor="ls")


def build(root: Path, output: Path) -> dict:
    master = (root / MASTER).read_bytes()
    font_data = (root / FONT).read_bytes()
    if sha(master) != MASTER_SHA or sha(font_data) != FONT_SHA:
        raise ValueError("unapproved_brand_source")
    image = Image.open(io.BytesIO(master))
    if image.size != (1254, 1254) or image.mode != "RGB":
        raise ValueError("invalid_master_geometry")
    title_face, tagline_face = Typeface(font_data, 600), Typeface(font_data, 450)
    contour_data = (root / CONTOURS).read_bytes()
    contours = json.loads(contour_data)
    glass, headset = (cutout(image, contours[name]) for name in ("glass", "headset"))
    files = {}

    def emit(path, data, role, **extra):
        path = Path(path)
        dest = output / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        meta = {"sha256": sha(data), "bytes": len(data), "role": role, **extra}
        if path.suffix == ".png":
            with Image.open(io.BytesIO(data)) as check:
                meta.update(width=check.width, height=check.height, mode=check.mode,
                            alpha=check.mode == "RGBA")
        files[path.as_posix()] = meta

    emit(FAMILY / "glass-master.png", png(glass), "transparent-glass-source", theme="both")
    emit(FAMILY / "headset-master.png", png(headset), "transparent-headset-source", theme="both")
    icons = {size: png((headset if size <= 40 else glass).resize((size, size), Image.Resampling.LANCZOS))
             for size in ICON_SIZES}
    for size, data in icons.items():
        emit(FAMILY / f"mark-{size}.png", data, "headset-only" if size <= 40 else "glass-mark", theme="both")
    encoded = base64.b64encode(png(glass)).decode("ascii")

    def svg_header(width, height, label):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
                f'aria-labelledby="brand-title brand-description">'
                f'<title id="brand-title">{label}</title>'
                '<desc id="brand-description">Brand V2: original raster with transparent glass contour; '
                'wordmark typography is outlined Inter. This is not a traced vector icon.</desc>')

    mark_svg = (svg_header(1024, 1024, "DJConnect")
                + f'<image width="1024" height="1024" href="data:image/png;base64,{encoded}"/>'
                + "</svg>\n").encode()
    emit(FAMILY / "mark.svg", mark_svg, "raster-backed-mark", theme="both")
    headset_encoded = base64.b64encode(png(headset)).decode("ascii")
    headset_svg = (svg_header(1024, 1024, "DJConnect")
                   + f'<image width="1024" height="1024" href="data:image/png;base64,{headset_encoded}"/>'
                   + "</svg>\n").encode()
    emit(FAMILY / "headset.svg", headset_svg, "raster-backed-headset-only", theme="both")

    wordmarks = {}
    for variant, width, height, title_size, baseline in (
        ("primary", 2048, 512, 240, 284),
        ("compact", 1728, 448, 216, 301),
    ):
        for theme, color, secondary in (
            ("light", "#111B48", "#34426A"),
            ("dark", "#F5F7FF", "#CAD8F9"),
        ):
            x = height + 64
            canvas = Image.new("RGBA", (width, height))
            canvas.paste(glass.resize((height, height), Image.Resampling.LANCZOS), (0, 0))
            title_face.draw(canvas, "DJConnect", title_size, x, baseline, color)
            svg = (svg_header(width, height, "DJConnect" + (" — " + TAGLINE if variant == "primary" else ""))
                   + f'<image width="{height}" height="{height}" href="data:image/png;base64,{encoded}"/>'
                   + title_face.svg("DJConnect", title_size, x, baseline, color))
            if variant == "primary":
                tagline_face.draw(canvas, TAGLINE, 80, x + 3, 402, secondary)
                svg += tagline_face.svg(TAGLINE, 80, x + 3, 402, secondary)
            svg = (svg + "</svg>\n").encode()
            wordmarks[variant, theme] = (canvas, svg)
            prefix = FAMILY / f"wordmark-{variant}-{theme}"
            emit(str(prefix) + ".png", png(canvas), "wordmark-" + variant, theme=theme)
            emit(str(prefix) + ".svg", svg, "raster-mark-outlined-wordmark-" + variant,
                 width=width, height=height, theme=theme)

    # Existing public paths remain valid; no symlinks in HA branding folders.
    for size in (256, 512, 1024):
        emit(f"assets/djconnect/djconnect-icon-{size}.png", icons[size], "mark-only-alias")
    emit("assets/djconnect/djconnect-icon.svg", mark_svg, "raster-backed-mark-alias")
    emit("assets/djconnect_icon.png", icons[512], "mark-only-alias")
    for theme, suffix in (("light", ""), ("dark", "-dark")):
        canvas, svg = wordmarks["primary", theme]
        emit(f"assets/djconnect/djconnect-logo{suffix}.svg", svg, "wordmark-primary-alias", theme=theme)
        for folder in HA_FOLDERS:
            prefix = "dark_" if theme == "dark" else ""
            for height, scale in ((256, ""), (512, "@2x")):
                size = (height * 4, height)
                emit(f"{folder}/{prefix}logo{scale}.png",
                     png(canvas.resize(size, Image.Resampling.LANCZOS)),
                     "ha-wordmark-primary", theme=theme)
    for folder in HA_FOLDERS:
        for size, suffix in ((256, ""), (512, "@2x")):
            emit(f"{folder}/icon{suffix}.png", icons[size], "ha-mark-only", theme="both")
    # Preserve the old explicit size alias; fit the full wordmark without distortion.
    legacy = Image.new("RGBA", (512, 256))
    legacy.alpha_composite(wordmarks["primary", "light"][0].resize((512, 128), Image.Resampling.LANCZOS), (0, 64))
    emit("assets/djconnect/djconnect-logo-512x256.png", png(legacy), "legacy-size-wordmark-alias")

    # Actual pixel size (no upscaled micro-icons) on both consumer theme backgrounds.
    preview = Image.new("RGB", (1360, 1560), "#FFFFFF")
    draw = ImageDraw.Draw(preview)
    for row, (theme, background, label) in enumerate((
        ("light", "#FFFFFF", "#111B48"), ("dark", "#091027", "#F5F7FF"),
        ("light", "#E4DBF8", "#111B48"),
    )):
        top = row * 520
        draw.rectangle((0, top, 1360, top + 519), fill=background)
        draw.text((24, top + 14), "Brand V2 / " + theme + " / icons at actual pixels", fill=label)
        x = 24
        for size in (16, 20, 24, 32, 40, 64, 128):
            icon = Image.open(io.BytesIO(icons[size]))
            preview.paste(icon, (x, top + 64), icon)
            draw.text((x, top + 210), str(size) + "px", fill=label)
            x += size + 42
        for variant, size, y in (("primary", (768, 192), 256), ("compact", (432, 112), 256)):
            mark = wordmarks[variant, theme][0].resize(size, Image.Resampling.LANCZOS)
            x = 20 if variant == "primary" else 856
            if variant == "compact":
                y = 292
            preview.paste(mark, (x, top + y), mark)
        draw.text((24, top + 472), "16–40px: headset only. 64px+: transparent glass silhouette. Original source RGB; outlined type.", fill=label)
    emit(FAMILY / "preview.png", png(preview), "visual-review-contact-sheet")

    manifest = {
        "schema_version": 1, "brand_version": "2.0.0", "brand_name": "DJConnect",
        "tagline_en": TAGLINE, "master": {"path": MASTER.as_posix(), "sha256": MASTER_SHA,
            "width": 1254, "height": 1254, "mode": "RGB", "alpha": False},
        "source_handoff_zip_sha256": "a0deec308d82c812875f80c509983fab595dd9745b241c2e5f46ff58fbb11197",
        "font": {"path": FONT.as_posix(), "sha256": FONT_SHA, "release": "Inter 4.1",
                 "license": "SIL-OFL-1.1", "title_weight": 600, "tagline_weight": 450, "optical_size": 32},
        "alpha_contours": {"path": CONTOURS.as_posix(), "sha256": sha(contour_data),
                           "micro_max_size": 40, "source_rgb_modified": False},
        "recipe_sha256": sha((root / "scripts/build_brand.py").read_bytes()),
        "tools": {"Pillow": PILLOW_VERSION, "fonttools": fontTools.__version__},
        "qualification": "source candidate; native/installed acceptance and protected producer pin required",
        "files": dict(sorted(files.items())),
    }
    path = output / FAMILY / "manifest.json"
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="Compare regenerated bytes; write nothing to source")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            manifest = build(args.root, output)
            names = list(manifest["files"]) + [(FAMILY / "manifest.json").as_posix()]
            drift = [name for name in names if not (args.root / name).is_file()
                     or (args.root / name).read_bytes() != (output / name).read_bytes()]
            if drift:
                # Causal readback distinguishes rendering drift from PNG framing
                # or encoder drift without silently accepting either kind.
                for name in drift:
                    if name.endswith(".png") and (args.root / name).is_file():
                        with Image.open(args.root / name) as old, Image.open(output / name) as new:
                            print(json.dumps({"path": name, "decoded_pixels_equal":
                                old.mode == new.mode and old.size == new.size and old.tobytes() == new.tobytes()}))
                raise SystemExit("Brand generation drift: " + ", ".join(drift))
    else:
        manifest = build(args.root, args.root)
    print(json.dumps({"brand_version": "2.0.0", "master_sha256": MASTER_SHA,
                      "generated_files": len(manifest["files"]), "verification": "PASS"}))


if __name__ == "__main__":
    main()
