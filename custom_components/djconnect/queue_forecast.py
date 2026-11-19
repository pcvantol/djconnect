"""Bounded observed-queue meanings and authored Forecast wording; no planning."""
from __future__ import annotations

import math


def capture_source(hass, observed):
    """Original observation admission, independent of visual/microphone interest."""
    try:
        from .domain.storage import STORE_KEY
        from .forecast_imagery import artist_authority
        domain = hass.data['djconnect']
        storage = domain[STORE_KEY]
        revision = storage.authority_revision
        manager = domain['session_runtime_manager']
        active = manager.current_active(observed.owner_profile_id)
        broadcast = active.broadcast
        source = manager._history_source_contexts[observed.session_id]
        values = dict(source)
        command, token = observed.command_revision, observed.visual_source
        entry = observed.integration_runtime.entry
        data, options = entry.data, entry.options
        source_allowed = artist_authority(hass, observed.integration_runtime,
            owner_profile_id=observed.owner_profile_id, expected_source=values)
        def allowed():
            try:
                current = manager.current_active(observed.owner_profile_id)
                return (hass.data.get('djconnect') is domain and domain.get(STORE_KEY) is storage
                    and storage._loaded and storage.authority_revision == revision
                    and domain.get('session_runtime_manager') is manager
                    and current is not None and current.session_id == observed.session_id
                    and current.broadcast is broadcast
                    and (observed.owner_profile_id, observed.session_id) not in manager._visual_ending
                    and manager._history_source_contexts.get(observed.session_id) is source
                    and source == values and observed.command_revision == command
                    and observed.visual_source is token and entry.data is data and entry.options is options
                    and domain['playback_observation_manager']._spotify_sessions.get(observed.owner_profile_id) is observed
                    and source_allowed())
            except Exception:
                return False
        return allowed, f'{observed.session_id}:{command}:{id(token)}:{revision}:{id(source)}'
    except Exception:
        return lambda: False, ''

PERSONAS = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')
COPY = {
    'nl': (
        ('Ik kijk even met je vooruit: {tracks}.', 'Een blik op wat er klaarstaat: {tracks}.',
         'Dit staat er voor de volgende ronde klaar: {tracks}.', 'Even vooruit naar de volgende namen: {tracks}.'),
        'De rode draad zoek ik hier in {genres}.',
        'Zo ziet de wachtrij er nu uit; als je iets verandert, beweeg ik met je mee.'),
    'en': (
        ('Let’s look a little ahead: {tracks}.', 'A look at what is lined up: {tracks}.',
         'Here is what is lined up for the next stretch: {tracks}.', 'A look ahead at the next names: {tracks}.'),
        'I’ll look for a musical thread through {genres}.',
        'That is the queue as it stands; if you change it, I’ll follow your lead.'),
    'de': (
        ('Schauen wir kurz nach vorn: {tracks}.', 'Ein Blick auf die bereitstehenden Titel: {tracks}.',
         'Das steht für die nächste Runde bereit: {tracks}.', 'Ein Blick auf die nächsten Namen: {tracks}.'),
        'Den musikalischen Faden suche ich hier in {genres}.',
        'So sieht die Warteschlange gerade aus; wenn du etwas änderst, gehe ich mit.'),
    'fr': (
        ('Regardons un peu la suite : {tracks}.', 'Un aperçu des titres en attente : {tracks}.',
         'Voici ce qui attend son tour : {tracks}.', 'Un regard sur les prochains noms : {tracks}.'),
        'Je chercherai le fil musical entre {genres}.',
        'Voilà la file actuelle ; si tu la modifies, je suivrai ton choix.'),
    'es': (
        ('Miremos un poco hacia delante: {tracks}.', 'Un vistazo a lo que está en la cola: {tracks}.',
         'Esto es lo que espera para el siguiente tramo: {tracks}.', 'Un vistazo a los próximos nombres: {tracks}.'),
        'Buscaré el hilo musical entre {genres}.',
        'Así está la cola ahora; si la cambias, seguiré tu elección.'),
}


def safe_text(value, limit=96):
    return (type(value) is str and 0 < len(value) <= limit
            and value == value.strip() and not any(ord(c) < 32 for c in value))


def valid_preview(value, now):
    """An internal value is never a renderer action or a new source lease."""
    if not isinstance(value, dict):
        return False
    deadline = value.get('deadline')
    wall_deadline = value.get('wall_deadline')
    items = value.get('items')
    return (type(deadline) in (int, float) and math.isfinite(deadline) and now < deadline <= now + 30
            and type(wall_deadline) in (int, float) and math.isfinite(wall_deadline)
            and isinstance(items, list) and 0 < len(items) <= 5
            and all(isinstance(i, dict) and safe_text(i.get('title')) and safe_text(i.get('artist'))
                    and isinstance(i.get('genres'), list) and len(i['genres']) <= 3
                    and all(safe_text(g, 48) for g in i['genres']) for i in items))


def realize_queue(items, locale, persona):
    """Names and artist genres are observed facts; no claimed sonic trajectory."""
    language = locale if locale in COPY else 'en'
    forms, genre_form, caveat = COPY[language]
    names = [f'“{i["title"]}” — {i["artist"]}' for i in items]
    conjunction = {'en':'and', 'nl':'en', 'de':'und', 'fr':'et', 'es':'y'}[language]
    tracks = (', '.join(names[:-1]) + f' {conjunction} ' + names[-1]
              if len(names) > 1 else names[0])
    genres = list(dict.fromkeys(g for i in items for g in i['genres']))[:3]
    index = PERSONAS.index(persona) if persona in PERSONAS else 0
    text = forms[index].format(tracks=tracks)
    if genres:
        text += ' ' + genre_form.format(genres=', '.join(genres))
    return text + ' ' + caveat
