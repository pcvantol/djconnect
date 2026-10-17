"""Exact accepted playback request presentation over the existing expression owner."""
from dataclasses import dataclass
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import time

from .narration_brief import NarrationBrief, NarratedText


@dataclass(frozen=True)
class PlaybackAcceptance:
    media_identity: str
    deadline: float
    key: str = 'playback_request'
    provider: str = 'Core'
    license: str = ''

    def eligible(self, identity, now):
        return identity == self.media_identity and now < self.deadline


@dataclass(frozen=True)
class PlaybackRequestBrief(NarrationBrief):
    """Core dispatch evidence; no catalog values are disclosed to the model."""


def outcome(selection, observed):
    matches = bool(observed.get('is_playing') and (
        observed.get('uri') in selection.get('uris', [])
        or (selection.get('context_uri') and observed.get('context_uri') == selection['context_uri'])))
    selection = deepcopy(selection)
    if (matches and selection.get('kind') == 'artist_tracks'
            and observed.get('uri') != selection['media'].get('uri')):
        # Shuffle may start another admitted track. Its actual readback owns
        # the name/art; the first submitted item is not proof of playback order.
        selection['media'] = {key: deepcopy(observed[key]) for key in (
            'uri', 'track_name', 'title', 'name', 'artist', 'artist_name',
            'album', 'album_name', 'album_image_url', 'media_image_url',
        ) if key in observed}
    return {'schema_version': 1, 'state': 'observed' if matches else 'dispatched',
            'observed_match': matches, 'selection': selection}


def _copy(receipt, language):
    media = receipt['selection']['media']
    label = media.get('track_name') or media.get('title') or media.get('name') or media.get('uri') or ''
    artist = media.get('artist') or media.get('artist_name') or ''
    album = media.get('album_name') or ''
    kind = receipt['selection']['kind']
    kinds = {
        'en': {'artist_tracks':'an artist selection','track':'the track','album':'the album','playlist':'the playlist'},
        'nl': {'artist_tracks':'een artiestselectie','track':'het nummer','album':'het album','playlist':'de playlist'},
        'de': {'artist_tracks':'eine Künstlerauswahl','track':'der Titel','album':'das Album','playlist':'die Playlist'},
        'fr': {'artist_tracks':'une sélection d’artiste','track':'le titre','album':'l’album','playlist':'la playlist'},
        'es': {'artist_tracks':'una selección del artista','track':'la canción','album':'el álbum','playlist':'la playlist'},
    }
    language = language if language in kinds else 'en'
    statuses = {
        'en': ('Playback is confirmed.', 'I requested playback; the player has not confirmed it yet.'),
        'nl': ('Het afspelen is bevestigd.', 'Ik heb het afspelen aangevraagd; de speler heeft de start nog niet bevestigd.'),
        'de': ('Die Wiedergabe ist bestätigt.', 'Ich habe die Wiedergabe angefordert; der Player hat den Start noch nicht bestätigt.'),
        'fr': ('La lecture est confirmée.', 'J’ai demandé la lecture ; le lecteur n’a pas encore confirmé le démarrage.'),
        'es': ('La reproducción está confirmada.', 'He solicitado la reproducción; el reproductor aún no ha confirmado el inicio.'),
    }
    bindings = {'{media_kind}': kinds[language].get(kind, kinds[language]['track']), '{title}':label,
                '{status}':statuses[language][0 if receipt['observed_match'] else 1]}
    if artist:
        bindings['{artist}'] = artist
    if album:
        bindings['{album}'] = album
    details = ' · '.join(str(v) for v in (bindings['{media_kind}'], label, artist, album) if v)
    return bindings, details + '. ' + bindings['{status}']


async def response(hass, runtime, receipt):
    """One reply after actual dispatch; enrichment never starts/retries playback."""
    from .ask_dj.dialogue import current_turn, DialogueError
    from .pipeline import realize_session_narration
    turn = current_turn.get()
    language = turn.style['language'] if turn else 'en'
    bindings, fallback = _copy(receipt, language)
    content = fallback
    # Only actual producer acceptance after the existing effect boundary admits
    # the bounded post-dispatch allowance. Caller data never sets this field.
    if (turn is not None and turn.effect_started and receipt.get('schema_version') == 1
            and receipt.get('state') in {'observed','dispatched'} and receipt.get('selection')):
        turn.accepted_playback_narration = True
    limit = 3 if turn is not None and turn.accepted_playback_narration else 2
    if turn is not None and limit - turn.agent_calls >= 2 and bindings.get('{title}'):
        def admission():
            if turn.frame.generation != turn.generation:
                raise DialogueError('conversation_context_changed')
            for validate in turn.effect_validators:
                validate()
        references = ('The provider accepted the exact submitted music request. '
            'The selection kind is {media_kind}; the selected title is {title}. '
            + ('The credited artist is {artist}. ' if '{artist}' in bindings else '')
            + ('The associated album is {album}. ' if '{album}' in bindings else '')
            + 'Insert the complete required {status} sentence unchanged. ')
        if receipt['selection']['kind'] == 'artist_tracks':
            references += ('This title is included in the submitted artist selection; do not promise which track starts first. '
                           'The provider list is not a claim of DJ musical selection or a reason it suits the listener. ')
        brief = PlaybackRequestBrief(
            PlaybackAcceptance(str(receipt['selection']['media'].get('uri') or ''), time.monotonic()+15),
            language, turn.style['persona'], turn.style['mood'], fallback, tuple(bindings),
            'Respond warmly to this actual playback request. Preserve its exact reached state; '
            'do not say music is playing when the provider start is only requested. '
            'No music fact, sound claim, guessed reason, future order or old playback substitution.',
            references, tuple(bindings.items()))
        await turn.guard()
        content = await realize_session_narration(hass, narration=brief, admission=admission,
            fallback_text=fallback, conf=runtime.config)
        await turn.guard()
    media = receipt['selection']['media']
    from .ask_dj import _images_from_context
    images = _images_from_context(hass, {"resolved_media":media}, {})
    return {'success': True, 'text': str(content), 'dj_text': str(content),
            'text_source': 'generated' if isinstance(content, NarratedText) else 'core',
            'is_generated_text': isinstance(content, NarratedText),
            'model_processing_basis': 'accepted_local_reply', 'playback_outcome':receipt,
            'resolved_media': media, 'media': media, 'images':images,
            'sources': [{'source':'spotify', 'kind':'source', 'title':'Spotify',
                         'uri':media.get('uri'),
                         'expires_at':(datetime.now(UTC)+timedelta(minutes=5)).isoformat()}],
            'playback_actions': [], 'items': []}


def failure(code, language, *, uncertain=False):
    """Action-local functional guidance without exposing provider payloads."""
    messages = {
        'output_unavailable': {
            'en': 'That speaker is no longer available. Open Spotify on it and choose the output again.',
            'nl': 'Die speaker is niet meer beschikbaar. Open Spotify daarop en kies de uitvoer opnieuw.',
            'de': 'Dieser Lautsprecher ist nicht mehr verfügbar. Öffne dort Spotify und wähle die Ausgabe erneut.',
            'fr': 'Cette enceinte n’est plus disponible. Ouvre Spotify dessus et choisis à nouveau la sortie.',
            'es': 'Ese altavoz ya no está disponible. Abre Spotify en él y vuelve a elegir la salida.',
        },
        'output_transfer_failed': {
            'en': 'Spotify has not confirmed the output change. Check the speaker before trying again.',
            'nl': 'Spotify heeft de uitvoerwissel niet bevestigd. Controleer de speaker voordat je het opnieuw probeert.',
            'de': 'Spotify hat den Ausgabewechsel nicht bestätigt. Prüfe den Lautsprecher vor einem neuen Versuch.',
            'fr': 'Spotify n’a pas confirmé le changement de sortie. Vérifie l’enceinte avant de réessayer.',
            'es': 'Spotify no ha confirmado el cambio de salida. Comprueba el altavoz antes de volver a intentarlo.',
        },
        'playback_failed': {
            'en': 'Spotify could not confirm this music request. I will not start different music instead.',
            'nl': 'Spotify kon dit muziekverzoek niet bevestigen. Ik start daarvoor geen andere muziek.',
            'de': 'Spotify konnte diese Musikanfrage nicht bestätigen. Ich starte stattdessen keine andere Musik.',
            'fr': 'Spotify n’a pas pu confirmer cette demande musicale. Je ne lance pas une autre musique à la place.',
            'es': 'Spotify no pudo confirmar esta solicitud musical. No iniciaré otra música en su lugar.',
        },
    }
    text = messages[code].get(language, messages[code]['en'])
    return {'success': False, 'error': code, 'error_scope': 'output' if code.startswith('output_') else 'playback_request',
            'text': text, 'dj_text': text, 'message': text, 'is_generated_text': False,
            'action_outcome': {'state': 'uncertain' if uncertain else 'rejected', 'retry_automatically': False},
            'images': [], 'playback_actions': [], 'items': []}
