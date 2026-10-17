"""Reported current-artist wording: actual shared owner, provider I/O fixtures."""

import unittest
from unittest.mock import patch
from tests import test_ask_dj_contextual_dialogue as shared


class CurrentArtistWordsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def test_explicit_current_artist_uses_fresh_music_context_in_all_five_languages(self):
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:

            async def status(hass, runtime, command, *args, **kwargs):
                self.assertEqual(command, "status")
                return {
                    "success": True,
                    "playback": {
                        "uri": "spotify:track:" + "N" * 22,
                        "title": "Current exact recording",
                        "artist": "Volbeat",
                        "is_playing": True,
                    },
                }

            with patch.object(f.core, "run_music_command", status):
                for i, (locale, question) in enumerate(
                    (
                        ("nl", "Wie is de artiest van huidig nummer"),
                        ("nl", "Wie is de artiest van het huidige nummer?"),
                        ("nl", "Wie is de artiest van dit nummer?"),
                        ("en", "Who is the artist of the current song?"),
                        ("de", "Wer ist der Künstler des aktuellen Liedes?"),
                        ("fr", "Qui est l’artiste du morceau actuel ?"),
                        ("es", "¿Quién es el artista de la canción actual?"),
                    )
                ):
                    answer, code = await f.request(
                        question, identifier="current-artist-words-" + str(i), language=locale
                    )
                    self.assertEqual(code, 200, answer)
                    self.assertEqual(
                        answer["intent"]["intent"], "current_artist_information", question
                    )
                    self.assertIn("Volbeat", answer["text"])
                    self.assertIn("Current exact recording", answer["text"])
                    self.assertEqual(answer["playback_actions"], [])
                    self.assertFalse(answer["history_persisted"])
            self.assertEqual(f.prompts, [])
        finally:
            await f.asyncTearDown()
