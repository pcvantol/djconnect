"""Targeted withdrawal includes prepared unwatched sources, preserving live audio."""
from types import SimpleNamespace
import time
import unittest

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()
from custom_components.djconnect.dj_response import (  # noqa: E402
    PrivateSpeechSource, invalidate_private_speech_sources,
)


class DeletionSpeechTests(unittest.TestCase):
    def test_prepared_unwatched_source_is_revoked_and_independent_live_is_valid(self):
        hass = SimpleNamespace(data={})
        old = PrivateSpeechSource(hass, lambda: None, expires_at=time.time() + 60, session_id='old')
        live = PrivateSpeechSource(hass, lambda: None, expires_at=time.time() + 60, session_id='live')
        dependent = PrivateSpeechSource(hass, lambda: None, expires_at=time.time() + 60,
                                       session_id='kept', entry_id='dependent-entry')
        independent = PrivateSpeechSource(hass, lambda: None, expires_at=time.time() + 60,
                                         session_id='kept', entry_id='independent-entry')
        invalidate_private_speech_sources(hass, session_id='old')
        invalidate_private_speech_sources(hass, entry_ids={'dependent-entry'})
        for revoked in (old, dependent):
            with self.assertRaises(PermissionError):
                revoked()
        live()
        independent()
        self.assertNotIn('tts_audio_source_watches', hass.data['djconnect'])

    def test_capacity_rejects_new_guard_without_evicting_an_existing_source(self):
        hass = SimpleNamespace(data={})
        guards = [PrivateSpeechSource(hass, lambda: None, expires_at=time.time() + 60,
                                     session_id=str(i)) for i in range(256)]
        with self.assertRaisesRegex(ValueError, 'speech_capacity'):
            PrivateSpeechSource(hass, lambda: None, expires_at=time.time() + 60)
        guards[0]()
        invalidate_private_speech_sources(hass, session_id='0')
        with self.assertRaises(PermissionError):
            guards[0]()
        guards[-1]()
