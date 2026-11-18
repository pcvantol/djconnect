from __future__ import annotations

from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tools.software_assurance import validate_action_runtimes


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = BytesIO(body)

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return False

    def read(self) -> bytes:
        return self.body.read()


class ActionRuntimeValidationTests(unittest.TestCase):
    def test_manifest_fetch_uses_exact_sha_raw_fallback_after_contents_api_failure(self) -> None:
        failure = HTTPError("https://api.github.com/contents/action.yml", 400, "Bad Request", None, None)
        raw_manifest = b"runs:\n  using: node24\n  main: dist/index.js\n"

        with patch.object(validate_action_runtimes, "urlopen", side_effect=[failure, _Response(raw_manifest)]) as urlopen:
            result = validate_action_runtimes._get_manifest(
                "token",
                "actions",
                "upload-artifact",
                "",
                "b7c566a772e6b6bfb58ed0dc250532a479d7789f",
            )

        self.assertEqual(result, raw_manifest.decode("utf-8"))
        requests = [call.args[0].full_url for call in urlopen.call_args_list]
        self.assertEqual(
            requests[1],
            "https://raw.githubusercontent.com/actions/upload-artifact/b7c566a772e6b6bfb58ed0dc250532a479d7789f/action.yml",
        )
