"""Explicit immutable V1 input for historical, already-consumed runner tests.

Never patch a runner manifest, source map, budget, grant, claim or clock. V2 is
deliberately rejected by those fixed runners. Only tests of the original V1
profile decoder use these independently hash-checked original catalogue bytes.
"""
from contextlib import contextmanager
from functools import wraps
import hashlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
V1_SHA256 = 'dfaa98a1659ef5673037da26f98136314b314beea8afe8e31af4ffd5bd6ac4e7'
CATALOGUE = ROOT / 'custom_components/djconnect/ask_dj/examples_v1.json'


@contextmanager
def original_catalogue_v1():
    raw = (ROOT / 'tests/fixtures/help_publication_v2/original-catalogue-v1-dfaa.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != V1_SHA256:
        raise AssertionError('historical_catalogue_fixture_changed')
    original_read = Path.read_bytes
    def read(path):
        return raw if path == CATALOGUE else original_read(path)
    with patch.object(Path, 'read_bytes', read):
        yield


def original_catalogue_v1_case(method):
    @wraps(method)
    def historical(*args, **kwargs):
        with original_catalogue_v1():
            return method(*args, **kwargs)
    return historical
