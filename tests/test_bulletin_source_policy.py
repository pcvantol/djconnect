"""Synthetic source-policy/locale/complete-text boundaries; no publisher/model calls."""
from dataclasses import replace
from itertools import combinations
import unittest

from tests.test_bulletin_intake import NOW, rss
from custom_components.djconnect.bulletin_intake import SOURCES, parse_feed
from custom_components.djconnect.bulletin_source_policy import (
    NOTICES, admitted_text, qualified_item, source_notice,
)


class BulletinSourcePolicyTests(unittest.TestCase):
    def test_all_five_locales_and_ten_actual_publisher_pairs_have_bounded_complete_notices(self):
        items = [parse_feed(source, rss(source), now=NOW)[0] for source in SOURCES]
        self.assertEqual(set(NOTICES), {'en', 'nl', 'de', 'fr', 'es'})
        for pair in combinations(items, 2):
            for locale in NOTICES:
                with self.subTest(sources=[i.source_id for i in pair], locale=locale):
                    notice = source_notice(pair, locale)
                    self.assertIn('DJConnect', notice)
                    self.assertTrue(all(i.source_title in notice for i in pair))
                    narrative = ' '.join(['synthetic'] * (60 - len(notice.split())))
                    full = narrative + '\n\n' + notice
                    self.assertTrue(admitted_text(full, pair, locale))
                    for changed in (narrative, full + ' altered', notice + '\n\n' + narrative,
                            full + '\n\n' + notice, full.replace('DJConnect', 'NASA')):
                        self.assertFalse(admitted_text(changed, pair, locale))
                    too_long = ' '.join(['synthetic'] * (111 - len(notice.split()))) + '\n\n' + notice
                    self.assertFalse(admitted_text(too_long, pair, locale))

    def test_unknown_locale_publisher_label_or_article_host_cannot_acquire_a_default_policy(self):
        pair = tuple(parse_feed(source, rss(source), now=NOW)[0] for source in SOURCES[:2])
        for locale in ('xx', '', None):
            with self.assertRaises(ValueError):
                source_notice(pair, locale)
        self.assertEqual(source_notice(pair, 'nl_NL'), source_notice(pair, 'nl'))
        for item in (replace(pair[0], license='unknown'), replace(pair[0], source_id='unknown'),
                replace(pair[0], source_title='Wrong publisher'),
                replace(pair[0], source_url='https://example.invalid/article')):
            self.assertFalse(qualified_item(item))
            self.assertFalse(admitted_text('not deliverable', (item, pair[1]), 'en'))
