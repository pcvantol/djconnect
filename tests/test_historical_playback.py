"""Explicit retained recording actions: exact identity, no search or autoplay."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


class HistoricalPlaybackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[1] / "custom_components/djconnect/historical_playback.py"
        spec = importlib.util.spec_from_file_location("djc_historical_playback_subject", path)
        cls.subject = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.subject
        spec.loader.exec_module(cls.subject)

    def row(self):
        return {
            "session_id": "saved-session",
            "entry_id": "entry-1",
            "kind": "playback_observed",
            "body": json.dumps(
                {
                    "provider": "Spotify",
                    "source_url": "https://open.spotify.com/track/" + "A" * 22,
                    "coverage": "observed_playing_not_full_listen",
                    "title": "Original recording",
                    "artist": "Original artist",
                    "album": "Original edition",
                    "album_uri": "spotify:album:" + "B" * 22,
                    "source_context": dict(
                        zip(
                            self.subject.SOURCE_FIELDS,
                            ("backend", "account", "entry", "provider-account"),
                            strict=True,
                        )
                    ),
                }
            ),
        }

    def test_closed_reference_rejects_uri_or_current_track_injection(self):
        expected = {"schema_version": 1, "session_id": "saved-session", "entry_id": "entry-1"}
        self.assertEqual(self.subject.checked_reference(expected), expected)
        for change in (
            {"uri": "spotify:track:" + "Z" * 22},
            {"schema_version": True},
            {"schema_version": 2},
            {"entry_id": ""},
            {"entry_id": []},
            {"session_id": "\n"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.subject.checked_reference({**expected, **change})

    def test_playback_target_is_original_recording_never_album_or_name_search(self):
        target = self.subject.recording(self.row())
        self.assertEqual(target["uri"], "spotify:track:" + "A" * 22)
        self.assertEqual(target["title"], "Original recording")
        self.assertEqual(target["album_uri"], "spotify:album:" + "B" * 22)
        self.assertNotIn("image_url", target)
        self.assertNotIn("query", target)

    def test_no_exact_track_or_original_source_means_no_action(self):
        for key, value in [
            ("provider", "Music Assistant"),
            ("source_url", "https://open.spotify.com/album/" + "A" * 22),
            ("source_url", "https://open.spotify.com/track/" + "A" * 22 + "?si=x"),
            ("source_context", {}),
            ("coverage", "full_listen"),
            ("title", ""),
        ]:
            row = self.row()
            body = json.loads(row["body"])
            body[key] = value
            row["body"] = json.dumps(body)
            with self.subTest(key=key, value=value):
                self.assertIsNone(self.subject.recording(row))
        for kind in ("conversation_dj", "conversation_user", "dj_publication", "dj_silence"):
            self.assertIsNone(self.subject.recording({**self.row(), "kind": kind}))

    def test_moment_prose_never_substitutes_for_original_recording_metadata(self):
        row = self.row()
        body = json.loads(row["body"])
        body["session_media_reference"] = {
            "subject_uri": "spotify:track:" + "C" * 22,
            "album_uri": "spotify:album:" + "D" * 22,
            "source_context": body["source_context"],
        }
        row.update(kind="dj_moment", body=json.dumps(body))
        self.assertIsNone(self.subject.recording(row))
        body["session_media_reference"]["subject_uri"] = "spotify:album:" + "D" * 22
        row["body"] = json.dumps(body)
        self.assertIsNone(self.subject.recording(row))

    def test_offers_are_opt_in_reference_only_and_never_execute_on_read(self):
        row = self.row()
        entry = {"entry_id": row["entry_id"], "session_id": row["session_id"], "kind": row["kind"]}
        self.assertEqual(self.subject.offer(row, entry, locale="nl"), entry)
        token = self.subject.offers_enabled.set(True)
        try:
            result = self.subject.offer(row, entry, locale="nl")
            action = result["playback_actions"][0]
            self.assertEqual(action["command"], "play_history_item")
            self.assertEqual(
                action["value"],
                {"schema_version": 1, "session_id": "saved-session", "entry_id": "entry-1"},
            )
            self.assertNotIn("spotify:", json.dumps(action))
            self.assertEqual(
                entry,
                {"entry_id": "entry-1", "session_id": "saved-session", "kind": "playback_observed"},
            )
        finally:
            self.subject.offers_enabled.reset(token)

    def test_all_five_languages_have_explicit_manual_play_labels(self):
        token = self.subject.offers_enabled.set(True)
        try:
            labels = {
                self.subject.offer(self.row(), {}, locale=lang)["playback_actions"][0]["label"]
                for lang in ("en", "nl", "de", "fr", "es")
            }
            self.assertEqual(len(labels), 5)
        finally:
            self.subject.offers_enabled.reset(token)
