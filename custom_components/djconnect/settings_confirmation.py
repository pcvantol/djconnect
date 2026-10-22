"""Core-authored acknowledgement of accepted choices, never music or model work."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import secrets

from .session_opening import SessionOpeningContext

FIELDS = ('mood', 'persona', 'presence')
_KEY = secrets.token_bytes(32)
COPY = {
    'nl': ('Even afstemmen',
        ('Ik ga met je mee: {changes}.', 'We slaan een nieuwe toon aan: {changes}.',
         'Nieuwe richting: {changes}.', 'Daar gaan we: {changes}.'),
        ('je mood is nu {mood}', 'ik vertel nu als je {persona}', 'je kiest {presence}'),
        ('Na deze bevestiging laat ik de muziek aan het woord; je vragen blijven welkom.',
         'Ik kom af en toe even bij je terug.', 'Ik laat verhalen en muziek elkaar de ruimte geven.',
         'Er is nu meer ruimte voor mijn verhalen tussen de muziek.')),
    'en': ('A little change of direction',
        ('I’m with you: {changes}.', 'Let’s take a new turn: {changes}.',
         'New direction: {changes}.', 'Here we go: {changes}.'),
        ('your Mood is now {mood}', 'I’m now your {persona}', 'you’ve chosen {presence}'),
        ('After this confirmation I’ll leave the music to speak; your questions are still welcome.',
         'I’ll drop in from time to time.', 'I’ll give stories and music room for each other.',
         'There’s now more room for my stories between the music.')),
    'de': ('Kurz neu abgestimmt',
        ('Ich gehe mit dir mit: {changes}.', 'Schlagen wir einen neuen Ton an: {changes}.',
         'Neue Richtung: {changes}.', 'Los geht’s: {changes}.'),
        ('dein Mood ist jetzt {mood}', 'ich bin jetzt dein {persona}', 'du hast {presence} gewählt'),
        ('Nach dieser Bestätigung lasse ich die Musik sprechen; deine Fragen bleiben willkommen.',
         'Ich melde mich ab und zu.', 'Ich lasse Geschichten und Musik ihren Raum.',
         'Zwischen der Musik ist jetzt mehr Platz für meine Geschichten.')),
    'fr': ('Un petit changement de cap',
        ('Je te suis : {changes}.', 'Prenons un nouveau ton : {changes}.',
         'Nouveau cap : {changes}.', 'C’est parti : {changes}.'),
        ('ton Mood est maintenant {mood}', 'je suis maintenant ton {persona}', 'tu as choisi {presence}'),
        ('Après cette confirmation, je laisse parler la musique ; tes questions restent les bienvenues.',
         'Je reviendrai de temps en temps.', 'Je laisserai de la place aux récits comme à la musique.',
         'Il y a maintenant plus de place pour mes récits entre la musique.')),
    'es': ('Un pequeño cambio de rumbo',
        ('Voy contigo: {changes}.', 'Tomemos un nuevo tono: {changes}.',
         'Nuevo rumbo: {changes}.', 'Allá vamos: {changes}.'),
        ('tu Mood es ahora {mood}', 'ahora soy tu {persona}', 'has elegido {presence}'),
        ('Tras esta confirmación dejaré hablar a la música; tus preguntas siguen siendo bienvenidas.',
         'Volveré de vez en cuando.', 'Dejaré espacio tanto a las historias como a la música.',
         'Ahora hay más espacio para mis historias entre la música.')),
}
PERSONAS = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')
PRESENCES = ('music_only', 'occasional', 'balanced', 'presenter')


def capability():
    return {'available': True, 'version': 1, 'trigger': 'accepted_user_change',
            'fields': list(FIELDS), 'one_per_operation': True, 'owner_only': True,
            'no_session': 'operation_confirmation_only', 'music_only': 'confirm_then_silent',
            'speech': 'existing_session_speech_respecting_announcement_output',
            'automatic_mood': 'no_confirmation', 'replay': 'original_identity_no_new_lease'}


def render(data):
    values = SessionOpeningContext(data['session_id'], **data['settings'], locale=data['locale']).values()
    copy = COPY[data['locale']]
    clauses = [copy[2][FIELDS.index(field)].format(**values) for field in data['changed_fields']]
    text = copy[1][PERSONAS.index(data['settings']['persona'])].format(changes='; '.join(clauses))
    if 'presence' in data['changed_fields']:
        text += ' ' + copy[3][PRESENCES.index(data['settings']['presence'])]
    elif 'mood' in data['changed_fields']:
        # The committed Mood describes the DJ's telling, never a claim that the
        # music, queue or physical output has been changed.
        tails = {
            'nl': ' Mijn manier van vertellen wordt {mood_meaning}.',
            'en': ' My way of telling will be {mood_meaning}.',
            'de': ' Meine Erzählweise wird {mood_meaning}.',
            'fr': ' Ma façon de raconter sera {mood_meaning}.',
            'es': ' Mi forma de contar será {mood_meaning}.',
        }
        text += tails[data['locale']].format(**values)
    elif 'persona' in data['changed_fields']:
        meaning = values['persona_meaning'].rstrip('.')
        text += ' ' + meaning[0].upper() + meaning[1:] + '.'
    return copy[0], text


def acceptance_data(*, owner, operation_id, before, after, session, locale, accepted_at, defaults_revision):
    """Called only inside the actual settings acceptance transaction."""
    changed = [f for f in FIELDS if before is None or getattr(before, f) != getattr(after, f)]
    if not changed:
        return None
    locale = str(locale).replace('_', '-').split('-', 1)[0].lower()
    locale = locale if locale in COPY else 'en'
    identifier = 'settings-' + hashlib.sha256((owner + ':' + operation_id).encode()).hexdigest()[:32]
    data = {'schema_version': 1, 'confirmation_id': identifier, 'changed_fields': changed,
            'settings': {f: getattr(after, f) for f in FIELDS}, 'locale': locale,
            'accepted_at': accepted_at, 'session_id': session['session_id'] if session else '',
            'settings_generation': session['generation'] if session else '',
            'settings_revision': session['revision'] if session else None,
            'defaults_revision': defaults_revision,
            'moment_id': 'moment-' + identifier.removeprefix('settings-') if session else None}
    data['title'], data['text'] = render(data)
    return data


@dataclass(frozen=True)
class AcceptedSettingsContext:
    encoded: str
    seal: str

    @classmethod
    def create(cls, data):
        # Only immutable closed server values survive; never an arbitrary
        # request, account/voice/provider configuration or narration body.
        encoded = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return cls(encoded, hmac.new(_KEY, encoded.encode(), 'sha256').hexdigest())

    def data(self):
        if not hmac.compare_digest(self.seal, hmac.new(_KEY, self.encoded.encode(), 'sha256').hexdigest()):
            raise ValueError('invalid_settings_confirmation')
        return json.loads(self.encoded)

    def matches(self, moment):
        try:
            d = self.data()
            title, text = render(d)
            return (moment.moment_id == d['moment_id'] and moment.session_id == d['session_id']
                    and moment.created_at == d['accepted_at']
                    and moment.moment_type.value == 'session'
                    and moment.knowledge_intent.intent_type.value == 'session_direction'
                    and moment.source_fact is None and not moment.source_attribution
                    and moment.observed_playback is None and moment.genre_transition is None
                    and moment.session_opening is None and moment.narration_acceptance is None
                    and moment.artwork_url is None and moment.actions == ()
                    and moment.presentation_intent.visibility.value == 'owner_only'
                    and tuple(c.value for c in moment.presentation_intent.delivery_channels) == ('owner',)
                    and moment.source_references == ('accepted_settings',)
                    and moment.title == title and moment.summary == title and moment.content == text
                    and moment.presentation_intent.dj_persona.value == d['settings']['persona']
                    and moment.presentation_intent.source_session_mood == d['settings']['mood']
                    and dict(moment.generation_metadata) == {'purpose': 'accepted_settings_change', 'validated': 'true'})
        except (ValueError, TypeError, KeyError):
            return False


def context(moment):
    value = getattr(moment, 'settings_confirmation', None)
    return value if type(value) is AcceptedSettingsContext and value.matches(moment) else None


def create_moment(data):
    from .session_runtime import (DJMoment, DJMomentType, KnowledgeIntent, KnowledgeIntentType,
                                 DJPersona, DJMomentVisibility, DeliveryChannel, _presentation_intent)
    title, text = render(data)
    intent = replace(_presentation_intent(data['settings']['mood'], DJPersona(data['settings']['persona']),
                     reading_characters=len(text), minimum_duration_seconds=15),
                     visibility=DJMomentVisibility.OWNER_ONLY, delivery_channels=(DeliveryChannel.OWNER,))
    return DJMoment(moment_id=data['moment_id'], session_id=data['session_id'], created_at=data['accepted_at'],
        moment_type=DJMomentType.SESSION,
        knowledge_intent=KnowledgeIntent(KnowledgeIntentType.SESSION_DIRECTION, 'Confirm accepted user settings.'),
        presentation_intent=intent, title=title, summary=title, content=text, artwork_url=None, actions=(),
        source_references=('accepted_settings',),
        generation_metadata=(('purpose', 'accepted_settings_change'), ('validated', 'true')),
        settings_confirmation=AcceptedSettingsContext.create(data))


def stage_moment(tx, repository, owner, data):
    """Stage the one history/semantic event in the SAME settings transaction."""
    moment = create_moment(data)
    from .persistence.summary import record_event_tx
    row = tx.fetchone('SELECT owner_profile_id,lifecycle_status,history_enabled FROM djconnect_persistent_sessions WHERE session_id=?',
                      (data['session_id'],))
    if row is None or row[0] != owner or row[1] != 'ACTIVE':
        raise PermissionError('session_context_changed')
    if row[2]:
        ids = repository._append_entries_tx(tx, owner, data['session_id'], [{
            'kind': 'dj_moment', 'reference_id': moment.moment_id, 'occurred_at': moment.created_at,
            'body': {'moment_id': moment.moment_id, 'moment_type': 'session', 'text': moment.content,
                     'summary': moment.summary, 'archive_basis': 'runtime_accepted_settings_v1',
                     'persona': data['settings']['persona'], 'mood': data['settings']['mood'],
                     'locale': data['locale'], 'generation_metadata': dict(moment.generation_metadata)}}])
        record_event_tx(tx, data['session_id'], 'dj_moment', moment.moment_id, ids[0] if ids else '')
    return moment

