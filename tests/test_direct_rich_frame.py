"""Actual Session projection plus complete original image container controls."""
import base64
from fractions import Fraction
import io
import struct
from types import SimpleNamespace
from unittest.mock import patch
import zlib

from tests import test_direct_rich_runtime as runtime_fixture
from custom_components.djconnect import direct_rich_frame as frame


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')


class DirectRichFrameTests(runtime_fixture.DirectRichRuntimeTests):
    async def test_original_milliseconds_are_exact_directional_rounding(self):
        for value in (1700000000.001, 1700000000.9999, 1700000000.000001):
            exact = Fraction(value) * 1000
            self.assertGreaterEqual(frame.utc_ms(value, upper=True), exact)
            self.assertLessEqual(frame.utc_ms(value), exact)
            self.assertLessEqual(frame.utc_ms(Fraction(value) + 120), exact + 120000)

    async def test_complete_original_PNG_rejects_trailing_second_image_animation_crc_and_truncation(self):
        self.assertTrue(frame.complete_image(PNG, 'image/png'))
        for body in (PNG + b'x', PNG + PNG, PNG[:-1], PNG[:35] + PNG):
            self.assertFalse(frame.complete_image(body, 'image/png'))
        corrupted = bytearray(PNG)
        corrupted[20] ^= 1
        self.assertFalse(frame.complete_image(bytes(corrupted), 'image/png'))
        payload = b'acTL' + struct.pack('>II', 1, 0)
        animation = struct.pack('>I', 8) + payload + struct.pack('>I', zlib.crc32(payload))
        self.assertFalse(frame.complete_image(PNG[:33] + animation + PNG[33:], 'image/png'))
        self.assertFalse(frame.complete_image(PNG, 'image/jpeg'))

    async def test_actual_decoded_baseline_and_progressive_JPEG_keep_one_complete_original_container(self):
        from PIL import Image
        from custom_components.djconnect import session_artwork
        for progressive in (False, True):
            with self.subTest(progressive=progressive):
                output = io.BytesIO()
                Image.new('RGB', (2, 3), (96, 112, 128)).save(output, format='JPEG', progressive=progressive)
                body = output.getvalue()
                self.assertTrue(frame.complete_image(body, 'image/jpeg'))
                dimensions, witness = session_artwork._decode_prepared(body)
                self.assertEqual(dimensions, (2, 3))
                self.assertIs(witness.body, body)
                self.assertEqual(witness.mime, 'image/jpeg')
                for invalid in (body[:-1], body + b'x', body + body):
                    self.assertFalse(frame.complete_image(invalid, 'image/jpeg'))

    async def test_stale_frame_drops_independent_content_without_renewing_observation(self):
        fields = dict(owner_profile_id='synthetic-owner', session_id=self.active.session_id,
            state='playing', media_identity='spotify:track:' + 'A' * 22,
            title='Synthetic track', artist='Synthetic artist')
        await self.manager.async_update_playback_projection(**fields)
        result = await self.authorize()
        first = self.read(result)
        self.assertIsNotNone(first['frame']['now_playing'])
        observed_mono, observed_wall = self.active.broadcast.passive_state_observed
        with patch.object(frame.time, 'monotonic', return_value=observed_mono + 121), \
                patch.object(frame.time, 'time', return_value=observed_wall + 121):
            second = self.read(result)
        self.assertEqual(second['frame']['state'], 'stale')
        self.assertIsNone(second['frame']['now_playing'])
        self.assertEqual(second['frame']['artwork'], [])
        self.assertEqual(second['frame']['observed_at_ms'], first['frame']['observed_at_ms'])
        self.assertEqual(second['frame']['expires_at_ms'], first['frame']['expires_at_ms'])
        self.assertNotEqual(second['frame']['frame_id'], first['frame']['frame_id'])
        self.assertEqual(second['frame']['delivery_sequence'], first['frame']['delivery_sequence'])
        self.assertEqual(second['purpose_expires_at_ms'], first['purpose_expires_at_ms'])

    async def test_actual_read_never_creates_or_warms_an_image_registry(self):
        result = await self.authorize()
        self.assertNotIn('session_images', self.domain)
        with patch('custom_components.djconnect.image_proxy.session_images', side_effect=AssertionError('No warming')):
            self.read(result)
        self.assertNotIn('session_images', self.domain)

    async def test_original_prepared_admission_is_reused_without_any_on_read_decode(self):
        from custom_components.djconnect import session_artwork as artwork
        dimensions, witness = artwork._decode_prepared(PNG)
        self.assertEqual(dimensions, (1, 1))
        asset = {'asset_id': 'A' * 32, 'body': PNG, 'mime': 'image/png', '_direct_rich_bytes': witness}
        registry = SimpleNamespace(assets={('synthetic-owner', self.active.session_id, ()): asset})
        descriptor = {'asset_id': 'A' * 32, 'width': 1, 'height': 1}
        with patch.object(artwork, '_decoded_size', side_effect=AssertionError('No hot-path decode')):
            self.assertEqual(frame._original_bytes(registry, descriptor), (PNG, 'image/png'))
            self.assertEqual(frame._original_bytes(registry, descriptor), (PNG, 'image/png'))
        asset['body'] = PNG + b'extra'
        from custom_components.djconnect.direct_rich_wire import RichError
        with self.assertRaises(RichError):
            frame._original_bytes(registry, descriptor)

    async def test_out_of_schema_optional_projection_is_omitted_without_truncating_or_blocking_frame(self):
        await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, state='playing',
            media_identity='spotify:track:' + 'A' * 22, title='Synthetic', artist='Synthetic')
        # Current RendererSafePlaybackProjection bounds labels to256 already.
        # Independently reject a future/invalid optional producer representation;
        # this does not claim that today's backend emits a513-character title.
        music, status = frame._music(self.active.broadcast, frame.time.monotonic())
        with patch.object(frame, '_music', return_value=({**music, 'track': 'X' * 513}, status)):
            result = await self.authorize()
        self.assertIsNone(result['frame']['now_playing'])
        self.assertEqual(result['frame']['now_playing_status']['reason'], 'source_not_qualified')
        self.assertEqual(result['frame']['playback_state'], 'playing')

    async def test_field_original_expiry_is_capped_to_shorter_frame_and_purpose(self):
        await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, state='playing',
            media_identity='spotify:track:' + 'A' * 22, title='Synthetic', artist='Synthetic')
        result = await self.authorize()
        purpose = self.rich.purposes[result['purpose_id']]
        attempt = purpose.context.attempt()
        limit = frame.utc_ms(frame.time.time()) + 500
        value, _ = frame.project(attempt, purpose_id=purpose.original.purpose_id,
            generation=purpose.generation, expires_ms=limit)
        self.assertEqual(value['expires_at_ms'], limit)
        self.assertLessEqual(frame._date_us(value['now_playing']['expires_at']), limit * 1000)
        with patch.object(frame.time, 'time', return_value=(limit + 1) / 1000):
            self.assertFalse(frame.final_current(attempt, value))

    async def test_expiry_crossed_during_actual_serialization_emits_no_old_content(self):
        await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, state='playing',
            media_identity='spotify:track:' + 'A' * 22, title='Synthetic', artist='Synthetic')
        result = await self.authorize()
        from custom_components.djconnect import direct_rich_runtime as runtime
        from custom_components.djconnect.direct_rich_wire import RichError
        original = runtime.canonical
        wall = frame.time.time()

        def serialize(value):
            data = original(value)
            clock.return_value = wall + 121
            return data

        with patch.object(frame.time, 'time', return_value=wall) as clock, \
                patch.object(runtime, 'canonical', side_effect=serialize):
            with self.assertRaises(RichError):
                self.read(result)

    async def test_actual_multibyte_backend_label_obeys_UTF8_not_only_scalar_limit(self):
        await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, state='playing',
            media_identity='spotify:track:' + 'A' * 22, title='音' * 200, artist='Synthetic')
        self.assertEqual(len(self.active.broadcast.state.playback.title), 200)
        self.assertEqual(len(self.active.broadcast.state.playback.title.encode()), 600)
        result = await self.authorize()
        self.assertIsNone(result['frame']['now_playing'])
        self.assertEqual(result['frame']['now_playing_status']['reason'], 'source_not_qualified')

    async def test_empty_optional_active_frame_crossing_deadline_during_serialization_is_not_emitted(self):
        result = await self.authorize()
        self.assertIsNone(result['frame']['now_playing'])
        self.assertIsNone(result['frame']['contribution'])
        self.assertEqual(result['frame']['artwork'], [])
        from custom_components.djconnect import direct_rich_runtime as runtime
        from custom_components.djconnect.direct_rich_wire import RichError
        original = runtime.canonical
        wall = frame.time.time()

        def serialize(value):
            encoded = original(value)
            clock.return_value = wall + 121
            return encoded

        with patch.object(frame.time, 'time', return_value=wall) as clock, \
                patch.object(runtime, 'canonical', side_effect=serialize):
            with self.assertRaises(RichError):
                self.read(result)
