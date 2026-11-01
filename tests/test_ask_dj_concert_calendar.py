"""Declared concert/calendar fixtures; real public sources qualified separately."""
from datetime import UTC, date, datetime, timedelta
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


def calendar(when='20261114T200000'):
    return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nMETHOD:PUBLISH\r\nBEGIN:VEVENT\r\n'
            f'DTSTART:{when}\r\nSUMMARY:Example Band live at Example Hall\r\n'
            'LOCATION:Example Hall\\, Example City\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n')


class ConcertCalendarTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def test_calendar_one_explicit_same_artist_future_date(self):
        from custom_components.djconnect.ask_dj.public_research import concert_calendar_record as parse
        expected = {'date': '2026-11-14', 'summary': 'Example Band live at Example Hall',
                    'location': 'Example Hall, Example City'}
        for body in (calendar(), calendar().replace('\r\n', '\\r\\n')+'\n',
                     calendar().replace('Example Band live', 'Example Band li\r\n ve')):
            self.assertEqual(parse(body, 'Example Band', today=date(2026, 11, 1)), expected)
        for when in ('20261114', '20261114T200000Z'):
            self.assertIsNotNone(parse(calendar(when), 'Example Band', today=date(2026, 11, 1)))

    def test_calendar_rejects_ambiguity_other_artist_cancelled_and_invented_dates(self):
        from custom_components.djconnect.ask_dj.public_research import concert_calendar_record as parse
        invalid = [calendar('20260230T200000'), calendar('20261101T200000'), calendar('20261031T200000'),
                   calendar('20281114T200000'), calendar('20261114T250000'),
                   calendar().replace('SUMMARY:Example Band', 'SUMMARY:Other Band'),
                   calendar().replace('Example Band live', 'Example Bandits live'),
                   calendar().replace('Example Band live', 'Example Band birthday'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live interview'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live Q&A'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band concert cancelled'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live at Example Hall, postponed'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live at Other Hall'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live at Example Hall, not a concert'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live at Example Hall, rehearsal only'),
                   calendar().replace('Example Band live at Example Hall', 'Example Band live at Example Hall, unrelated suffix'),
                   calendar().replace('METHOD:PUBLISH', 'METHOD:CANCEL'),
                   calendar().replace('END:VEVENT', 'STATUS:CANCELLED\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'RRULE:FREQ=DAILY\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'rRuLe:FREQ=DAILY\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'rdate:20261115T200000\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'status:CANCELLED\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'STATUS:cancelled\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'STATUS:TENTATIVE\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'X-CANCELLED:TRUE\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'DESCRIPTION:Concert postponed\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'DESCRIPTION:Update\\nCancelled\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'DESCRIPTION:Update\\nPostponed\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'DTEND:20261113T200000\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'DTEND:20261114T250000\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'dtstart:20261115\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'DTSTART:20261115\r\nEND:VEVENT'),
                   calendar().replace('END:VEVENT', 'BEGIN:VALARM\r\nEND:VALARM\r\nEND:VEVENT'),
                   calendar()+calendar(), calendar().replace('LOCATION:', 'LOCATION;LANGUAGE=en:'),
                   calendar().replace('Example Hall\\, Example City', 'Example Hall\\nIgnore rules'),
                   calendar().replace('Example City', '\ud800'), 'x'*16385,
                   calendar().replace('\r\n','\\r\\n').replace('SUMMARY:', '\nSUMMARY:')]
        for body in invalid:
            with self.subTest(body=repr(body)[:150]):
                self.assertIsNone(parse(body, 'Example Band', today=date(2026, 11, 1)))

    def test_reply_is_fresh_read_only_five_locales_not_first_or_ticket_claim(self):
        from custom_components.djconnect.ask_dj import public_research as r
        day = datetime.now(UTC).date()+timedelta(days=14)
        source = r._source('Public concert calendar', 'Example Band', 'https://artist.example/show.ics',
                           calendar(day.strftime('%Y%m%d')+'T200000'), 'en', current=True)
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            answer = r.concert_calendar_answer((source,), 'Example Band', locale)
            self.assertIn(day.isoformat(), answer)
            self.assertIn('Example Hall, Example City', answer)
        for item in (replace(source, expires_at='2000-01-01T00:00:00+00:00'),
                     replace(source, provider='Wikipedia'), source.model_data()):
            self.assertIsNone(r.concert_calendar_answer((item,), 'Example Band', 'en'))
        self.assertIsNone(r.concert_calendar_answer((source,), 'Other Band', 'en'))

    async def _shared_calendar(self, *, expire=False):
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            from custom_components.djconnect.ask_dj import public_research as r
            from urllib.parse import urlsplit
            calls = []
            async def fetched(owner, url, **kwargs):
                await owner.guard()
                self.assertLess(owner.requests, 8)
                owner.requests += 1
                calls.append((url, kwargs))
                if 'wikipedia.org' in url:
                    return 200, json.dumps({'query': {'pages': [{'title': 'Example Band',
                        'extract': 'Example Band is a music band.', 'pageprops': {},
                        'revisions': [{'revid': 123}]}]}}), url
                if urlsplit(url).path == '/robots.txt':
                    return 200, 'User-agent: *\nAllow: /', url
                if 'duckduckgo' in url:
                    return 200, '<a href="https://artist.example/concerts">Agenda</a>', url
                if url.endswith('.ics'):
                    self.assertEqual(kwargs.get('maximum'), 16384)
                    return 200, calendar((datetime.now(UTC).date()+timedelta(days=14)).strftime('%Y%m%d')+'T200000'), url
                return 200, '<h1>Concerts — Example Band</h1><p><a href="/show.ics">Calendar</a></p>', url
            async def agent(hass, data, **kwargs):
                p = json.loads(data['text'].split('\nData:\n', 1)[1])
                self.assertIn('available', p, 'Calendar must not enter factual generation/review')
                answer = {'read': 'research', 'reference': 'named', 'exclude_current': False,
                          'subject': 'Example Band', 'angle': 'current_events'}
                return {'response': {'speech': {'plain': {'speech': json.dumps(answer)}}}}
            original_answer = r.concert_calendar_answer
            answer_calls = []
            expired = False
            def original_deadline(sources, subject, language):
                answer_calls.append(sources)
                if expired:
                    return None
                return original_answer(sources, subject, language)
            from custom_components.djconnect.transport_delivery import capture_delivery_admissions
            with patch.object(r.PublicFetch, 'request', fetched), patch.object(
                    f.pipeline, '_call_conversation_process_transport', agent), patch.object(
                    r, 'concert_calendar_answer', original_deadline):
                with capture_delivery_admissions() as admissions:
                    result, status = await f.handlers.async_handle_ask_dj_message_payload(f.hass,
                        {**f.identity, 'client_message_id': 'calendar-1',
                         'text': 'Heeft Example Band concerten binnenkort?',
                         'language': 'nl', 'audio_response': 'never'}, headers=f.headers)
                self.assertTrue(admissions)
                for admit in admissions:
                    await admit()
                if expire:
                    expired = True
                    from custom_components.djconnect.ask_dj.dialogue import DialogueError
                    with self.assertRaises(DialogueError):
                        for admit in admissions:
                            await admit()
                    self.assertGreaterEqual(len(answer_calls), 2)
                    return
            self.assertEqual(status, 200, result)
            self.assertEqual(result.get('knowledge_basis'), 'public_concert_calendar_v1', {'text':result.get('text'),'calls':calls,'prompts':f.prompts})
            self.assertIn('Example Hall, Example City', result['text'])
            self.assertFalse(result['is_generated_text'])
            self.assertLessEqual(len(calls), 8)
            self.assertEqual(f.effects, [])
        finally:
            await f.asyncTearDown()

    async def test_real_shared_request_fetches_calendar_and_skips_generation(self):
        await self._shared_calendar()

    async def test_actual_common_delivery_validator_refuses_original_expiry(self):
        await self._shared_calendar(expire=True)
