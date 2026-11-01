"""Connected Album web-evidence boundaries; source and model replies are fixtures."""
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from tests import test_personal_dj_narration_album as fixtures


class AlbumWebNarrationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.AlbumNarrationTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.AlbumNarrationTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.AlbumNarrationTest()
        await self.fixture.asyncSetUp()
        self.base = self.fixture.base
        self.normal_fetch = self.fixture.fetch
        self.normal_model = self.fixture.model
        self.base.fetch, self.base.model = self.fetch, self.model
        self.mode = ''
        self.answer = ('Volgens Robin Vale rende hij bij de filmopnames voor Paper Windows 1 '
                       'van Nora Vale 1 tussen de opnames op sokken naar de cameramensen. '
                       'Stille regie, letterlijk.')
        self.web_url = 'https://director.example.test/recording-story'

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def fetch(self, fetch, url, **kwargs):
        host = urlsplit(url).hostname
        if host not in {'html.duckduckgo.com', 'director.example.test'}:
            return await self.normal_fetch(fetch, url, **kwargs)
        await fetch.guard()
        self.assertLess(fetch.requests, fetch.maximum_requests)
        fetch.requests += 1
        self.fixture.urls.append(url)
        self.fixture.owners.append(fetch)
        if urlsplit(url).path == '/robots.txt':
            return 200, 'User-agent: *\nDisallow: /' if self.mode == 'robots' else 'User-agent: *\nAllow: /', url
        if host == 'html.duckduckgo.com':
            query = parse_qs(urlsplit(url).query)['q'][0]
            self.assertEqual(query, 'Nora Vale 1 "Paper Windows 1" recording interview behind the scenes')
            return 200, '<a href="'+self.web_url+'">A filming account</a>', url
        title = 'Paper Windows 1 II' if self.mode == 'sequel' else 'Paper Windows 1'
        artist = 'Other Artist' if self.mode == 'wrong-artist' else 'Nora Vale 1'
        byline = '' if self.mode == 'no-byline' else '<meta name="author" content="Robin Vale">'
        competing = '<p>For Other Work, we began another project.</p>' if self.mode in {'other-work', 'unmarked-switch'} else ''
        html = ('<html lang="en"><head>'+byline+'</head><body>'
            f'<p>I directed a music film called ‘{title}’ for {artist}.</p>'+competing+
            ("<p>During the music film recordings for ‘Paper Windows 1’ by Nora Vale 1, I ran on my socks to the camera operators to give them directions.</p>" if not competing else '<p>Only between recordings I ran on my socks to the camera operators to give them directions.</p>')
            + '</body></html>')
        if self.mode in {'sequel','wrong-artist','no-byline'}:
            html = html.replace('During the music film recordings for ‘Paper Windows 1’ by Nora Vale 1, I ran', 'Only between recordings I ran')
        if self.mode == 'page-unavailable':
            return 404, '', url
        return 200, html, url

    async def model(self, hass, data, **kwargs):
        payload = json.loads(data['text'].split('\nData:\n')[1])
        sources = payload.get('public_music_research', payload.get('evidence', {}).get('public_music_research', {})).get('sources', [])
        web = next((s for s in sources if s['provider'] == 'Public web'), None)
        if web is None:
            return await self.normal_model(hass, data, **kwargs)
        self.fixture.calls.append(data['text'])
        if len(self.fixture.calls) % 2:
            if self.fixture.after_draft:
                await self.fixture.after_draft()
            value = self.answer
        else:
            span = next(p for p in web['evidence_spans'] if 'I ran' in p['text'])
            first, second = self.answer.split('. ', 1)
            value = json.dumps({'supported':True, 'unsupported_claims':[], 'temporal_claims':[],
                'language_ok':True, 'style_ok':True, 'album_focus_preserved':True,
                'review_schema':'source_id_review_v1', 'claim_checks':[
                    {'text':first+'.', 'kind':'relationship', 'evidence_ids':[span['id']]},
                    {'text':second, 'kind':'dj_appreciation', 'evidence_ids':[]}]})
        return {'response':{'speech':{'plain':{'speech':value}}}}

    async def test_actual_owner_publish_reopen_and_retained_speech_keep_attributed_web_source(self):
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_speech import resolve_retained
        moment = await self.base.publish()
        self.assertIsNotNone(moment, self.base.debug)
        self.assertEqual(moment.content, self.answer)
        self.assertEqual(len(self.fixture.calls), 2)
        self.assertLessEqual(len(self.fixture.urls), 12)
        self.assertTrue(all(f is self.fixture.owners[0] for f in self.fixture.owners))
        sources = moment.as_dict()['sources']
        self.assertEqual(len(sources), 3)
        web = next(s for s in sources if s['provider'] == 'Public web')
        self.assertEqual(web['url'], self.web_url)
        self.assertEqual(web['usage_basis'], 'public_page_short_reference')
        self.assertEqual(web['attributed_author'], 'Robin Vale')
        self.assertEqual(web['wikidata_id'], '')
        self.assertEqual(web['revision_url'], '')
        self.assertNotIn('untrusted_excerpt', web)
        self.assertNotIn('literal_passages', web)
        for prompt in self.fixture.calls:
            self.assertNotIn(self.fixture.artist_id, prompt)
            self.assertNotIn(self.base.catalog['release_date'], prompt)
            self.assertNotIn('profile-a', prompt)
        await self.base.manager.async_end(owner_profile_id='profile-a', session_id=moment.session_id)
        await self.base.fixture.service.async_close()
        await self.base.fixture.service.async_initialize()
        page = await query_service(self.base.hass, self.base.history).async_timeline_page('profile-a', moment.session_id)
        saved = next(e for e in page['entries'] if e.get('moment_id') == moment.moment_id)
        self.assertEqual(saved['text'], self.answer)
        self.assertEqual(saved['sources'], sources)
        before = len(self.fixture.urls)
        descriptor, _ = await resolve_retained(self.base.hass, self.base.history, 'profile-a',
            {'session_id':moment.session_id, 'entry_id':saved['entry_id']})
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual(len(self.fixture.urls), before)

    async def rejected(self, mode):
        self.mode = mode
        moment = await self.base.publish()
        self.assertIsNotNone(moment, self.base.debug)
        self.assertNotIn('Public web', {s['provider'] for s in moment.as_dict()['sources']})
        self.assertTrue(any('duckduckgo.com' in url for url in self.fixture.urls))
        self.assertFalse(any('I ran on my socks' in p for p in self.fixture.calls))

    async def test_missing_byline_is_not_author_evidence(self):
        await self.rejected('no-byline')

    async def test_other_artist_does_not_supply_album_evidence(self):
        await self.rejected('wrong-artist')

    async def test_quoted_sequel_is_not_a_prefix_match(self):
        await self.rejected('sequel')

    async def test_another_marked_work_withdraws_document_antecedent(self):
        await self.rejected('other-work')

    async def test_robots_refusal_does_not_supply_snippet_evidence(self):
        await self.rejected('robots')

    async def test_failed_actual_page_does_not_supply_snippet_evidence(self):
        await self.rejected('page-unavailable')

    async def test_unmarked_sequel_cannot_borrow_a_later_target_marker(self):
        from custom_components.djconnect import album_narration as album
        from custom_components.djconnect.ask_dj import public_research as research
        identity = ('album', self.fixture.group_id, 'Paper Windows 1', self.fixture.mbid, 'Q1', 'Nora Vale 1', 'Group')
        for opening in ('I directed Paper Windows 1 II for Nora Vale 1.',
                        "I directed ‘Paper Windows 1’ for Nora Vale 1. For Other Work, I recorded another film."):
            page = research.PageText()
            page.feed('<meta name="author" content="Robin Vale"><p>'+opening+'</p>'
                      '<p>Only between recordings I ran on my socks.</p>'
                      '<p>‘Paper Windows 1’ was also mentioned.</p>')
            self.assertIsNone(album.web_source(page, self.web_url, identity, ''))

    def test_album_budget_is_internal_and_other_research_keeps_original_limits(self):
        from custom_components.djconnect.ask_dj.public_research import PublicFetch, AlbumPublicFetch, ConcertPublicFetch
        self.assertEqual((PublicFetch.maximum_requests, PublicFetch.html_maximum), (8, 128*1024))
        self.assertEqual((AlbumPublicFetch.maximum_requests, AlbumPublicFetch.html_maximum), (12, 512*1024))
        self.assertEqual((ConcertPublicFetch.maximum_requests, ConcertPublicFetch.html_maximum), (8, 512*1024))

    async def test_actual_shared_fetch_preserves_json_robots_caps_and_stops_at_album_budget(self):
        import aiohttp
        from custom_components.djconnect.ask_dj import public_research as research
        self.enterContext(patch.object(aiohttp, 'ClientError', type('ClientError', (Exception,), {}), create=True))
        class Content:
            def __init__(self, count): self.count = count
            async def iter_chunked(self, size):
                for offset in range(0, self.count, size):
                    yield b'x' * min(size, self.count-offset)
        class Response:
            status = 200
            headers = {}
            def __init__(self, kind, count): self.content_type, self.content = kind, Content(count)
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        class Session:
            def __init__(self, kind, count): self.kind, self.count = kind, count
            def get(self, *args, **kwargs): return Response(self.kind, self.count)
            async def close(self): pass
        async def guard(): pass
        for owner, kind, count, maximum, allowed in (
            (research.PublicFetch, 'text/html', 128*1024, 128*1024, True),
            (research.PublicFetch, 'text/html', 128*1024+1, 128*1024, False),
            (research.AlbumPublicFetch, 'text/html', 512*1024, 128*1024, True),
            (research.AlbumPublicFetch, 'text/html', 512*1024+1, 128*1024, False),
            (research.AlbumPublicFetch, 'application/json', 128*1024+1, 128*1024, False),
            (research.AlbumPublicFetch, 'text/html', 16385, 16384, False),
            (research.ConcertPublicFetch, 'text/html', 512*1024, 128*1024, True),
            (research.ConcertPublicFetch, 'text/html', 512*1024+1, 128*1024, False),
            (research.ConcertPublicFetch, 'application/json', 128*1024+1, 128*1024, False),
            (research.ConcertPublicFetch, 'text/html', 16385, 16384, False),
            (research.ConcertPublicFetch, 'text/calendar', 16384, 16384, True),
            (research.ConcertPublicFetch, 'text/calendar', 16385, 16384, False),
        ):
            with self.subTest(owner=owner, kind=kind, count=count):
                async with owner(guard) as fetch:
                    fetch.session = Session(kind, count)
                    if allowed:
                        self.assertEqual((await fetch.request(self.web_url, maximum=maximum))[0], 200)
                    else:
                        with self.assertRaisesRegex(research.ResearchUnavailable, 'response_size'):
                            await fetch.request(self.web_url, maximum=maximum)
        async with research.AlbumPublicFetch(guard) as fetch:
            fetch.session = Session('text/html', 1)
            fetch.requests = 12
            with self.assertRaisesRegex(research.ResearchUnavailable, 'public_research_budget'):
                await fetch.request(self.web_url)
