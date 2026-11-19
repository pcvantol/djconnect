"""Bounded GHCR read probe; never asserts write rights or package absence."""
import base64
import json
import os
import urllib.error
import urllib.request

HOST = 'https://ghcr.io'
REPOSITORY = 'djconnect-music-dj/djconnect-verification-platform'
TAGS = frozenset(('latest', '1.1', '1.1.0', 'sha-f05773616a1a', '1.1.0-f05773616a1a'))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def probe(actor, token, request):
    result = {'registry_read': 'UNKNOWN', 'selected_tags_visible_first_page': None,
              'write_permission': 'NOT_TESTED', 'absence': 'NOT_ASSERTED'}
    if not actor or ':' in actor or not token:
        return result
    auth = base64.b64encode((actor + ':' + token).encode()).decode()
    try:
        code, raw = request(HOST + '/token?scope=repository:' + REPOSITORY + ':pull', 'Basic ' + auth)
        if code != 200:
            return result
        data = json.loads(raw)
        bearer = data.get('token') if isinstance(data, dict) else None
        if not isinstance(bearer, str) or not bearer or '\n' in bearer or '\r' in bearer:
            return result
        code, raw = request(HOST + '/v2/' + REPOSITORY + '/tags/list', 'Bearer ' + bearer)
        if code != 200:
            return result
        data = json.loads(raw)
        tags = data.get('tags') if isinstance(data, dict) else None
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            return result
        result['registry_read'] = 'VISIBLE'
        result['selected_tags_visible_first_page'] = len(TAGS.intersection(tags))
    except Exception:
        pass
    return result

def request(url, authorization):
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, headers={'Authorization': authorization, 'Accept':'application/json'})
    try:
        with opener.open(req, timeout=10) as response:
            return response.status, response.read(1048577) if int(response.headers.get('Content-Length', 0)) <= 1048576 else b''
    except urllib.error.HTTPError as error:
        return error.code, b''

def main():
    print(json.dumps(probe(os.getenv('GITHUB_ACTOR', ''), os.getenv('GITHUB_TOKEN', ''), request), sort_keys=True))

if __name__ == '__main__':
    main()
