"""Synthetic provider boundary for catalogue Golden, not a Core answer factory."""
from copy import deepcopy
from datetime import UTC, datetime
import re


def handle(method, path, query, body, state, tracks):
    """(handled, payload); never read a case's expected answer or model output."""
    album = {'id':'b'*22,'uri':'spotify:album:'+'b'*22,
        'name':'Beyond Hell/Above Heaven','release_date':'2008-05-06',
        'release_date_precision':'day','images':[{'url':'https://i.scdn.co/image/synthetic-catalogue-album'}],
        'artists':deepcopy(tracks[0]['artists']),
        'total_tracks':3}
    playlist = {'id':'k'*22, 'uri':'spotify:playlist:'+'k'*22,
        'name':'Cooking collection' if state.get('collection') == 'cooking' else 'Quiet collection',
        'images':[], 'owner':{'id':'synthetic-owner','display_name':'Synthetic owner'},
        'tracks':{'total':3}, 'type':'playlist'}
    if method in {'PUT','POST','DELETE'}:
        return False, None
    if path == '/search':
        value = ' '.join(query.get('q', [])).casefold()
        kinds = set(','.join(query.get('type', [])).split(','))
        named = 'volbeat' in value or 'beyond hell' in value
        exact_artist = bool(re.fullmatch(r'(?:artist:)?[\"]?volbeat[\"]?',value.strip()))
        cooking = bool(re.search(r'cook|koken|kochen|cuisin|cocin',value))
        quiet = bool(re.search(r'quiet|relax|rustig|ruhig|calm|tranquil',value))
        if cooking or quiet:
            state['collection'] = 'cooking' if cooking else 'quiet'
            playlist['name'] = 'Cooking collection' if cooking else 'Quiet collection'
        return True, {
            'artists':{'items':[deepcopy(tracks[0]['artists'][0])] if exact_artist and 'artist' in kinds else []},
            'tracks':{'items':deepcopy(tracks) if named and 'track' in kinds else []},
            'albums':{'items':[album] if named and 'album' in kinds else []},
            'playlists':{'items':[playlist] if (cooking or quiet) and 'playlist' in kinds else []}}
    if path == '/me/playlists':
        return True, {'items':[playlist], 'next':None, 'total':1}
    if path == '/me/player/recently-played':
        return True, {'items':[{'track':deepcopy(tracks[0]), 'played_at':datetime.now(UTC).isoformat(),
                              'context':{'type':'album','uri':album['uri']}}], 'next':None}
    if path == '/albums/'+'b'*22:
        return True, album
    if path == '/albums/'+'b'*22+'/tracks':
        return True, {'items':deepcopy(tracks), 'next':None,'total':3}
    if path == '/artists/'+'a'*22+'/albums':
        return True, {'items':[album], 'next':None, 'total':1}
    if path == '/artists/'+'a'*22:
        return True, {**deepcopy(tracks[0]['artists'][0]),'genres':['rock'],'images':[]}
    if path == '/artists/'+'a'*22+'/top-tracks':
        return True, {'tracks':deepcopy(tracks)}
    if path == '/artists':
        return True, {'artists':[{**deepcopy(tracks[0]['artists'][0]),'genres':['rock'],'images':[]}]
            if query.get('ids') == ['a'*22] else []}
    if path.startswith('/artists/'):
        return True, {}
    if path == '/playlists/'+'k'*22:
        return True, playlist
    if path == '/playlists/'+'k'*22+'/tracks':
        return True, {'items':[{'track':deepcopy(t)} for t in tracks], 'next':None, 'total':3}
    if path.startswith('/tracks/'):
        found = next((t for t in tracks if path == '/tracks/'+t['id']), None)
        return True, deepcopy(found) if found else {}
    return False, None
