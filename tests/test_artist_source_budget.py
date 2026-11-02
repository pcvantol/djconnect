"""Shared retrieval admission, with explicit synthetic source transports."""
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_personal_dj_narration as owner


class ArtistSourceBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        owner.PersonalDJNarrationTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        owner.PersonalDJNarrationTest.tearDownClass()

    def test_independent_publisher_precedes_another_wikipedia_language(self):
        from custom_components.djconnect import official_artist_research as official
        from custom_components.djconnect.ask_dj import public_research as research
        async def scenario():
            calls = []
            async def guard():
                pass
            # Explicit boundary fixture for a primary lookup and its translated
            # edition each consuming three original requests. No source rights
            # or semantic acceptance is created by this scheduling test.
            async def wikipedia(fetch, subject, question, locale, **kwargs):
                calls.append(locale)
                fetch.requests += 3
                return SimpleNamespace(language=locale, entity_id='Q1', provider='Wikipedia')
            async def website(fetch, identity, topic):
                calls.append('independent')
                if fetch.maximum_requests-fetch.requests < 3:
                    return None
                fetch.requests += 3
                return SimpleNamespace(provider='Artist website')
            with patch.object(research, 'wikipedia', wikipedia), patch.object(official, 'website_reference', website):
                sources = await official.artist_references('Test group', 'A documented music story', 'nl',
                    guard, identity=('artist', 'public-id', 'Test group', 'Group', 'Q1'),
                    roles=('Group',), topic='recording')
            self.assertEqual(calls, ['nl', 'independent'])
            self.assertEqual([s.provider for s in sources], ['Wikipedia', 'Artist website'])
        asyncio.run(scenario())
