"""Exact URL classification for external-source fixtures, never network authority."""
from urllib.parse import urlsplit

WIKIPEDIA_HOSTS = frozenset(f'{locale}.wikipedia.org' for locale in ('en', 'nl', 'de', 'fr', 'es'))
SEARCH_HOSTS = frozenset({'duckduckgo.com', 'html.duckduckgo.com'})


def fixture_location(url):
    """Reject malformed/authenticated/non-HTTPS fixture locations before matching."""
    if not isinstance(url, str) or url != url.strip() or any(ord(c) < 32 for c in url):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme == 'https' and parsed.hostname and parsed.username is None
                and parsed.password is None and parsed.port in (None, 443)):
            return parsed
    except ValueError:
        pass
    return None


def fixture_host(url):
    parsed = fixture_location(url)
    return parsed.hostname if parsed is not None else None


def wikipedia_api_fixture(url):
    parsed = fixture_location(url)
    return bool(parsed is not None and parsed.hostname in WIKIPEDIA_HOSTS
                and parsed.path == '/w/api.php')


def exclude_non_english_fixture(url):
    host = fixture_host(url)
    return host is None or host in (WIKIPEDIA_HOSTS - {'en.wikipedia.org'}) | SEARCH_HOSTS
