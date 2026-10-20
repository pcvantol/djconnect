"""User entrypoints, version boundaries and preserved technical information."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
ASSET = "https://raw.githubusercontent.com/pcvantol/djconnect/7e14e5970b3f68d33d243ae6bab2b281fad59bb2/assets/djconnect/brand-v2/mark-128.png"
DEEPLINK = "https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration"


class HacsUserDocumentationTest(unittest.TestCase):
    def test_hacs_still_uses_readme_and_source_documentation(self):
        self.assertIs(json.loads((ROOT / "hacs.json").read_text())["render_readme"], True)
        manifest = json.loads((ROOT / "custom_components/djconnect/manifest.json").read_text())
        self.assertEqual(manifest["documentation"], "https://github.com/pcvantol/djconnect")
        self.assertEqual(manifest["version"], "4.0.0-rc.1")
        for name in ("README.md", "info.md"):
            text = (ROOT / name).read_text()
            self.assertIn(manifest["version"], text)
            self.assertIn("3.3.1", text)
            self.assertIn(DEEPLINK, text)
            self.assertIn(
                "Restart Home Assistant" if name == "README.md" else "restart Home Assistant", text
            )
            self.assertIn("Add integration", text)
        self.assertEqual(
            parse_qs(urlsplit(DEEPLINK).query),
            {"owner": ["pcvantol"], "repository": ["djconnect"], "category": ["integration"]},
        )

    def test_compact_theme_independent_approved_brand_is_identical_on_both_surfaces(self):
        class Images(HTMLParser):
            def __init__(self):
                super().__init__()
                self.images = []

            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    self.images.append(dict(attrs))

        readme = (ROOT / "README.md").read_text()
        info = (ROOT / "info.md").read_text()
        self.assertTrue(60 <= len(readme.splitlines()) <= 110)
        self.assertLess(len(info.splitlines()), len(readme.splitlines()))
        for text in (readme, info):
            self.assertIn("Your music. Your DJ.", text)
            p = Images()
            p.feed(text)
            self.assertEqual(
                p.images, [{"src": ASSET, "alt": "DJConnect", "width": "64", "height": "64"}]
            )
            for old in (
                "Muziekbediening met karakter",
                "<picture",
                "<source",
                "760",
                "YOUR PERSONAL AI DJ",
            ):
                self.assertNotIn(old, text)
        manifest = json.loads((ROOT / "assets/djconnect/brand-v2/manifest.json").read_text())
        path = "assets/djconnect/brand-v2/mark-128.png"
        self.assertEqual(
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
            manifest["files"][path]["sha256"],
        )
        self.assertEqual(manifest["files"][path]["theme"], "both")

    def test_user_requirements_do_not_turn_one_provider_into_a_global_precondition(self):
        text = (ROOT / "README.md").read_text()
        for required in (
            "conversation agent",
            "STT/TTS are optional",
            "Spotify Premium",
            "Developer app Client ID",
            "HTTPS",
            "Music Assistant",
            "usable player",
            "Later / manual",
            "without Spotify login",
            "existing **Profile**",
            "same LAN",
            "2.4 GHz",
        ):
            self.assertIn(required, text)
        for locale, name in (
            ("en", "installation.md"),
            ("nl", "nl.md"),
            ("de", "de.md"),
            ("fr", "fr.md"),
            ("es", "es.md"),
        ):
            guide = (ROOT / "docs/user" / name).read_text()
            with self.subTest(locale=locale):
                for term in (
                    "3.3.1",
                    "4.0.0-rc.1",
                    "Spotify Direct",
                    "Music Assistant",
                    "Client ID",
                    "Client Secret",
                    "HTTPS",
                    "Profile",
                    DEEPLINK,
                ):
                    self.assertIn(term, guide)
                self.assertTrue(any(term in guide for term in ("Later", "handmatig", "manual")))
        stable = (ROOT / "docs/user/stable-3.3.1.md").read_text()
        self.assertIn("both STT", stable)
        self.assertIn("and TTS", stable)
        self.assertIn("Later/manual exists in this version too", stable)
        self.assertIn("backend comes before the new Profile", stable)
        candidate = (ROOT / "docs/user/installation.md").read_text()
        self.assertIn("Choose an existing Profile or create a new one", candidate)
        spotify = (ROOT / "docs/user/spotify-direct.md").read_text()
        self.assertIn("exact redirect URI shown by the current wizard", spotify)
        self.assertIn("reauthorize", spotify)

    def test_pairing_precedes_profile_in_each_actual_wizard_journey(self):
        cases = [
            ("README.md", "## Start your first session"),
            ("docs/user/installation.md", "## Follow the wizard"),
            ("docs/user/nl.md", "## Installeren en starten"),
            ("docs/user/de.md", "## Installieren und starten"),
            ("docs/user/fr.md", "## Installer et démarrer"),
            ("docs/user/es.md", "## Instalar e iniciar"),
            ("docs/user/stable-3.3.1.md", "# Install and start"),
        ]
        for name, heading in cases:
            journey = (ROOT / name).read_text().split(heading, 1)[1].split("\n## ", 1)[0]
            steps = re.split(r"(?m)^\d+\. ", journey)[1:]
            pairing = next(i for i, step in enumerate(steps) if "iPhone/Watch" in step)
            profile = next(i for i, step in enumerate(steps) if "Profile" in step)
            with self.subTest(page=name):
                self.assertLess(pairing, profile)
                self.assertIn("Assist", steps[pairing])

    def test_hacs_surfaces_contain_no_engineering_or_live_retired_client_advertising(self):
        forbidden = r"APNs|bootstrap_proof|djci_|djcboot_|(?:GET|POST) /api|Engineering Platform|Software Assurance|release\.sh|```|Windows"
        for name in ("README.md", "info.md"):
            self.assertIsNone(re.search(forbidden, (ROOT / name).read_text()), name)

    def test_new_navigation_links_resolve_and_info_uses_absolute_targets(self):
        pages = [
            ROOT / "README.md",
            ROOT / "info.md",
            ROOT / "docs/README.md",
            *sorted((ROOT / "docs/user").glob("*.md")),
            ROOT / "docs/technical/ENTITIES_AND_SUPPORT.md",
        ]
        for page in pages:
            text = page.read_text()
            for target in re.findall(r"\[[^]\n]+\]\(([^)]+)\)", text):
                target = unquote(target.split("#", 1)[0])
                if not target or urlsplit(target).scheme:
                    continue
                self.assertTrue((page.parent / target).resolve().exists(), (str(page), target))
                self.assertNotEqual(page.name, "info.md", "HA info links must be absolute")

    def test_technical_content_and_original_checklist_survive_relocation(self):
        push = (ROOT / "docs/technical/PUSH_NOTIFICATIONS.md").read_text()
        for required in (
            "missing_bootstrap_proof",
            "bootstrap_proof_expired",
            "bootstrap_proof_used",
            "install_id_mismatch",
            "bootstrap_rate_limited",
            "APNs registratie",
            "djconnect.test_apns_push",
            "dry-run",
            "08:00",
            "about once per hour",
        ):
            self.assertIn(required, push)
        admin = (ROOT / "docs/technical/ENTITIES_AND_SUPPORT.md").read_text()
        for required in (
            "music_backend_revision",
            "pairing, device tokens, Ask DJ history, Music DNA",
            "push registrations",
            "not a listening-history list",
        ):
            self.assertIn(required, admin)
        history = (
            (ROOT / "docs/release/maintainer.md")
            .read_text()
            .split("````text\n", 1)[1]
            .rsplit("````", 1)[0]
        )
        self.assertEqual(
            hashlib.sha256(history.encode()).hexdigest(),
            "a05f4eec3033e08f579de2eb7048e9fa220c7378e1890b31f75d84e024aae20d",
        )
        self.assertIn("grants no", (ROOT / "docs/release/maintainer.md").read_text())
