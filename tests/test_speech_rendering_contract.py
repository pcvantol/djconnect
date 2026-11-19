"""Regression coverage for the renderer-neutral Speech Rendering contract."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "technical" / "SPEECH_RENDERING_CONTRACT.md"


class SpeechRenderingContractTest(unittest.TestCase):
    """Keep speech consumption local, ordered and free of server renderer detail."""

    def _contents(self) -> str:
        return " ".join(DOCUMENT.read_text().split())

    def test_contract_preserves_renderer_safe_immutable_input_and_order(self) -> None:
        contents = self._contents()

        for required in (
            "Presentation identity",
            "source DJMoment identity and type",
            "ordered immutable Speech Segments",
            "preserve both order and semantic Speaker Role",
            "must not merge, split, reorder, rewrite or infer segments",
            "`DJ` and `Sidekick` are semantic roles",
            "Speech Presentation is text-only",
        ):
            self.assertIn(required, contents)

    def test_contract_excludes_renderer_and_tts_information(self) -> None:
        contents = self._contents()

        for required in (
            "Planner state",
            "Knowledge internals",
            "TTS provider selection",
            "voice identifiers",
            "renderer configuration",
            "no audio, speech asset, locale, room-routing instruction",
        ):
            self.assertIn(required, contents)

    def test_role_mapping_and_fallback_are_renderer_local(self) -> None:
        contents = self._contents()

        for required in (
            "Speaker Role -> configured local voice -> configured local TTS provider",
            "This mapping is entirely renderer-local.",
            "When Speech Audio is unavailable, a host may render Speech Text.",
            "the Presentation remains valid",
            "No fallback may cause server-side regeneration",
        ):
            self.assertIn(required, contents)

    def test_renderer_relationships_and_deferred_scope_are_explicit(self) -> None:
        contents = self._contents()

        for required in (
            "Universal Receiver Speech Presentation Component",
            "VibeCast consumes the same Presentation Projection",
            "Apple and Home Assistant may later act as Audio Renderer Hosts.",
            "Google TV and VibeCast renderer implementation",
            "multi-audio-renderer policy",
            "cloud speech",
        ):
            self.assertIn(required, contents)


if __name__ == "__main__":
    unittest.main()
