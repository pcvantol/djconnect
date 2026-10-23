"""Synthetic bounded RSS/Atom/time/HTTP tests; no live news or model calls."""
import asyncio
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import unittest

from tests.test_persistence_platform import PersistenceService  # noqa: F401
from custom_components.djconnect import bulletin_intake as intake

NOW = 1792695600.0


def rss(source, *, age=5, date=None, guid="original", suffix="one", title="Synthetic science mission starts today", description="A short public announcement."):
    date = date if date is not None else format_datetime(datetime.fromtimestamp(NOW - age, timezone.utc))
    return ("<rss><channel><title>Publisher</title><item><guid>" + escape(guid) + "</guid>"
        "<title>" + escape(title) + "</title><description>" + escape(description) + "</description>"
        "<link>https://" + source.article_hosts[0] + "/news/" + suffix + "</link>"
        "<pubDate>" + escape(date) + "</pubDate></item></channel></rss>").encode()


class BulletinIntakeTests(unittest.TestCase):
    def setUp(self):
        self.source = intake.SOURCES[0]

    def parse(self, body, now=NOW):
        return intake.parse_feed(self.source, body, now=now)

    def test_fixed_five_sources_have_https_rights_and_no_mutable_user_config(self):
        self.assertTrue(5 <= len(intake.SOURCES) <= 7)
        self.assertEqual(len({s.source_id for s in intake.SOURCES}), len(intake.SOURCES))
        for source in intake.SOURCES:
            self.assertTrue(source.url.startswith("https://"))
            self.assertTrue(source.rights_url.startswith("https://"))
        alien = intake.FeedSource("alien", "Alien", "https://example.invalid/feed", ("example.invalid",), "unknown", "")
        with self.assertRaises(intake.IntakeError):
            intake.parse_feed(alien, rss(alien), now=NOW)

    def test_original_publication_window_boundary_never_fetch_time(self):
        self.assertEqual(len(self.parse(rss(self.source, age=1799))), 1)
        for age in (1800, 1801, -1, -30000):
            self.assertEqual(self.parse(rss(self.source, age=age)), ())
        item = self.parse(rss(self.source, age=1799))[0]
        self.assertEqual(item.observed_at, NOW)
        self.assertFalse(item.fresh(NOW + 1))
        for date in ("", "not a date", "Thu, 22 Oct 2026 10:00:00"):
            self.assertEqual(self.parse(rss(self.source, date=date)), ())

    def test_explicit_timezones_and_actual_cbs_colon_offset_are_equivalent(self):
        iso = intake.publication_time("2026-10-22T10:00:00+02:00")
        self.assertEqual(iso, intake.publication_time("Thu, 22 Oct 2026 10:00:00 +02:00"))
        self.assertEqual(iso, intake.publication_time("2026-10-22T08:00:00Z"))

    def test_flat_wallclock_cannot_keep_an_old_intake_item_fresh(self):
        item = intake.parse_feed(self.source, rss(self.source, age=1790),
            now=NOW, monotonic=100)[0]
        self.assertTrue(item.fresh(NOW, monotonic=109))
        self.assertFalse(item.fresh(NOW, monotonic=110))

    def test_atom_requires_published_not_refreshed_updated_and_one_alternate_link(self):
        source = intake.SOURCES[-1]
        stamp = datetime.fromtimestamp(NOW - 20, timezone.utc).isoformat()
        body = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>urn:synthetic</id>'
            '<title>Independent synthetic economic announcement</title><published>' + stamp + '</published>'
            '<updated>' + stamp + '</updated><summary>A brief summary.</summary>'
            '<link href="https://ec.europa.eu/eurostat/news/one"/></entry></feed>').encode()
        items = intake.parse_feed(source, body, now=NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].guid, "urn:synthetic")
        self.assertEqual(intake.parse_feed(source, body.replace(b"<published>", b"<old>").replace(b"</published>", b"</old>"), now=NOW), ())
        duplicate_link = body.replace(b"</entry>", b'<link href="https://ec.europa.eu/other"/></entry>')
        self.assertEqual(intake.parse_feed(source, duplicate_link, now=NOW), ())

    def test_guid_rotation_and_tracking_query_do_not_duplicate_a_url(self):
        first = rss(self.source)
        second = first.replace(b"original", b"new-guid").replace(b"/news/one<", b"/news/one?utm_source=duplicate<")
        body = first.replace(b"</channel></rss>", b"") + second.split(b"<item>", 1)[1].join((b"<item>", b""))
        items = self.parse(body)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_url, "https://www.cbs.nl/news/one")
        self.assertEqual(self.parse(second)[0].fingerprint, items[0].fingerprint)

    def test_no_external_link_credentials_private_network_or_fragment(self):
        for url in ("http://www.cbs.nl/news", "https://www.cbs.nl.evil.invalid/news",
                    "https://127.0.0.1/news", "https://secret@www.cbs.nl/news",
                    "https://www.cbs.nl:8123/news", "https://www.cbs.nl/news#fragment"):
            body = rss(self.source).replace(b"https://www.cbs.nl/news/one", escape(url).encode())
            self.assertEqual(self.parse(body), ())

    def test_xml_dtd_entities_utf16_depth_size_and_non_feed_are_rejected(self):
        bad = ('<!DOCTYPE rss [<!ENTITY x "external instruction">]>'
            '<rss><channel><item><title>&x;</title></item></channel></rss>')
        for body in (bad.encode(), bad.encode("utf-16"), b"<html/>", b"<rss>",
                     b"x" * (intake.MAX_BYTES + 1), b"<rss><channel>" + b"<x>" * 30 + b"</x>" * 30 + b"</channel></rss>"):
            with self.subTest(prefix=body[:12]), self.assertRaises(intake.IntakeError):
                self.parse(body)

    def test_html_scripts_are_removed_not_executed_and_no_full_article_field(self):
        items = self.parse(rss(self.source, description="<p>Short factual metadata.</p><script>secret()</script>"))
        self.assertEqual(items[0].description, "Short factual metadata.")
        self.assertFalse(hasattr(items[0], "article_body"))
        self.assertEqual(self.parse(rss(self.source, title="a" * 241)), ())

    def test_explicit_rights_never_inherit_a_broader_publisher_default(self):
        original = rss(self.source)
        declarations = (
            b'<copyright>Restricted third-party material</copyright>',
            b'<dc:rights xmlns:dc="http://purl.org/dc/elements/1.1/">All rights reserved</dc:rights>',
            b'<rights xmlns="urn:synthetic-rights">Unknown conditions</rights>',
            b'<license>CC-BY-4.0</license>',  # Not separately qualified per-item permission.
            b'<link rel="license" href="https://example.invalid/terms"/>',
            b'<copyright/>',  # Absence of text is not permission either.
        )
        for declaration in declarations:
            for closing in (b'</item>', b'</channel>'):
                with self.subTest(declaration=declaration, level=closing):
                    self.assertEqual(self.parse(original.replace(closing, declaration + closing)), ())
        self.assertEqual(len(self.parse(original)), 1)

    def test_exact_knmi_feed_owner_notice_uses_reviewed_cc0_default_without_new_lease(self):
        source = next(source for source in intake.SOURCES if source.source_id == 'knmi')
        notice = b'<copyright>Copyright: KNMI, https://www.knmi.nl/</copyright>'
        body = rss(source, age=1799).replace(b'</channel>', notice + b'</channel>')
        items = intake.parse_feed(source, body, now=NOW, monotonic=100)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].license, 'CC0-1.0')
        self.assertEqual(items[0].published_at, NOW-1799)
        self.assertEqual(items[0].monotonic_deadline, 101)
        self.assertEqual(intake.parse_feed(source, body, now=NOW+1, monotonic=101), ())

    def test_feed_rights_wrappers_cannot_hide_unqualified_conditions(self):
        for source in intake.SOURCES:
            original = rss(source)
            for declaration in (b'<copyright>Restricted third party</copyright>',
                    b'<rights/>', b'<link rel="license" href="https://example.invalid/terms"/>'):
                body = original.replace(b'</channel>', b'<metadata>' + declaration + b'</metadata></channel>')
                with self.subTest(source=source.source_id, declaration=declaration):
                    self.assertEqual(intake.parse_feed(source, body, now=NOW), ())

    def test_knmi_notice_is_not_generic_feed_or_item_permission(self):
        notice = b'<copyright>Copyright: KNMI, https://www.knmi.nl/</copyright>'
        knmi = next(source for source in intake.SOURCES if source.source_id == 'knmi')
        variants = (notice.replace(b'KNMI,', b'Other publisher,'),
            notice.replace(b'https://www.knmi.nl/', b'https://example.invalid/'),
            notice.replace(b'<copyright>', b'<copyright scope="all">'),
            notice.replace(b'<copyright>', b'<copyright><extra/>'),
            b'<rights>Copyright: KNMI, https://www.knmi.nl/</rights>',
            b'<copyright xmlns="urn:other">Copyright: KNMI, https://www.knmi.nl/</copyright>',
            b'<copyright/>', notice + notice, b'<metadata>' + notice + b'</metadata>',
            notice + b'<license>CC0-1.0</license>')
        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(intake.parse_feed(knmi,
                    rss(knmi).replace(b'</channel>', value+b'</channel>'), now=NOW), ())
        for source in intake.SOURCES:
            with self.subTest(source=source.source_id):
                self.assertEqual(intake.parse_feed(source,
                    rss(source).replace(b'</item>', notice+b'</item>'), now=NOW), ())
                if source is not knmi:
                    self.assertEqual(intake.parse_feed(source,
                        rss(source).replace(b'</channel>', notice+b'</channel>'), now=NOW), ())
        restricted = rss(knmi).replace(b'</item>', b'<rights>Restricted</rights></item>')
        self.assertEqual(intake.parse_feed(knmi,
            restricted.replace(b'</channel>', notice+b'</channel>'), now=NOW), ())

    def test_atom_rights_at_feed_or_entry_are_unqualified_and_cannot_override_each_other(self):
        source = intake.SOURCES[-1]
        stamp = datetime.fromtimestamp(NOW - 5, timezone.utc).isoformat()
        original = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
            '<title>Synthetic independent economic announcement</title><published>' + stamp + '</published>'
            '<link href="https://ec.europa.eu/eurostat/news/one"/></entry></feed>').encode()
        for closing in (b'</entry>', b'</feed>'):
            for declaration in (b'<rights>All rights reserved</rights>',
                    b'<link rel="license" href="https://creativecommons.org/licenses/by/4.0/"/>'):
                with self.subTest(level=closing, declaration=declaration):
                    self.assertEqual(intake.parse_feed(source,
                        original.replace(closing, declaration + closing), now=NOW), ())
        self.assertEqual(len(intake.parse_feed(source, original, now=NOW)), 1)

    def test_restricted_item_does_not_poison_its_unrestricted_sibling(self):
        restricted = rss(self.source).replace(b'</item>', b'<copyright>Restricted</copyright></item>')
        sibling = rss(self.source, suffix="two", title="Different synthetic announcement about employment")
        body = restricted.replace(b'</channel></rss>',
            sibling.split(b'<item>', 1)[1].join((b'<item>', b'')))
        result = self.parse(body)
        self.assertEqual([item.source_url for item in result], ['https://www.cbs.nl/news/two'])


class Content:
    def __init__(self, body):
        self.body = body

    async def iter_chunked(self, limit):
        for pos in range(0, len(self.body), limit):
            yield self.body[pos:pos + limit]


class Response:
    def __init__(self, status, body=b"", headers=None):
        self.status, self.content, self.headers = status, Content(body), headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class HTTP:
    def __init__(self):
        self.calls = []
        self.reply = lambda source: Response(200, rss(source), {"ETag": '"same"'})

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        source = next(s for s in intake.SOURCES if s.url == url)
        return self.reply(source)


class BulletinCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_feed_fetch_cannot_restart_the_original_publication_lease(self):
        clock = [100.0]
        class Slow(Response):
            async def __aenter__(self):
                clock[0] += 20
                return self
        http = HTTP()
        http.reply = lambda source: Slow(200, rss(source, age=1790))
        collector = intake.FeedCollector(http, monotonic=lambda: clock[0])
        self.assertEqual(await collector.collect(now=NOW), ())

    async def test_http_sdk_failure_does_not_escape_into_session_or_skip_other_sources(self):
        http = HTTP()
        normal = http.get
        def broken(url, **kwargs):
            if url == intake.SOURCES[0].url:
                raise RuntimeError("synthetic-http-sdk-failure")
            return normal(url, **kwargs)
        http.get = broken
        collector = intake.FeedCollector(http)
        self.assertEqual(len(await collector.collect(now=NOW)), 4)

    async def test_polling_conditional304_preserves_original_clocks_and_expires_without_refresh(self):
        http = HTTP()
        collector = intake.FeedCollector(http)
        first = await collector.collect(now=NOW)
        self.assertEqual(len(first), 5)
        self.assertEqual(await collector.collect(now=NOW + 299), first)
        self.assertEqual(len(http.calls), 5)
        http.reply = lambda source: Response(304)
        self.assertEqual(await collector.collect(now=NOW + 300), first)
        for _, args in http.calls[5:]:
            self.assertEqual(args["headers"]["If-None-Match"], '"same"')
            self.assertFalse(args["allow_redirects"])
            self.assertNotIn("Authorization", args["headers"])
        self.assertEqual(await collector.collect(now=NOW + 1800), ())

    async def test_outage_redirect_malformed_oversized_are_backed_off_per_source(self):
        http = HTTP()
        cases = {"cbs": Response(302, headers={"Location": "https://evil.invalid"}),
            "knmi": Response(200, b"<html/>"), "nasa": Response(503),
            "eea": Response(200, b"x" * (intake.MAX_BYTES + 1))}
        http.reply = lambda source: cases.get(source.source_id, Response(200, rss(source)))
        collector = intake.FeedCollector(http)
        self.assertEqual(len(await collector.collect(now=NOW)), 1)
        await collector.collect(now=NOW + 300)
        self.assertEqual(len(http.calls), 6)  # Only successful Eurostat polls.
        self.assertTrue(all(url != "https://evil.invalid" for url, _ in http.calls))

    async def test_concurrent_calls_do_not_duplicate_polls_and_cancellation_propagates(self):
        http = HTTP()
        collector = intake.FeedCollector(http)
        await asyncio.gather(collector.collect(now=NOW), collector.collect(now=NOW))
        self.assertEqual(len(http.calls), 5)
        class Cancel(Response):
            async def __aenter__(self):
                raise asyncio.CancelledError
        http.reply = lambda source: Cancel(200)
        with self.assertRaises(asyncio.CancelledError):
            await collector.collect(now=NOW + 300)

    async def test_validator_header_injection_is_never_returned_to_http(self):
        http = HTTP()
        http.reply = lambda source: Response(200, rss(source), {"ETag": 'bad\r\nsecret', "Last-Modified": "x" * 257})
        collector = intake.FeedCollector(http)
        await collector.collect(now=NOW)
        await collector.collect(now=NOW + 300)
        self.assertTrue(all("If-None-Match" not in args["headers"] for _, args in http.calls))
        self.assertTrue(all("If-Modified-Since" not in args["headers"] for _, args in http.calls))
