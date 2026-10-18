"""Immutable start choices for one Core-authored welcome; never playback authority."""
from dataclasses import dataclass

PERSONAS = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')
MOODS = ('chill', 'groove', 'energy', 'party')
PRESENCES = ('music_only', 'occasional', 'balanced', 'presenter')
PERSONA_NAMES = ('Home DJ', 'Radio DJ', 'Club DJ', 'Festival DJ')
MOOD_NAMES = ('Chill', 'Groove', 'Energy', 'Party')

# Only the honest local fallback is composed here. Qualified HA expression uses
# the same meanings and names, but chooses its own narrative/rhythm.
COPY = {
    'en': (
        'Your DJ session', 'Welcome! I’m your {persona}: {persona_meaning}. With {mood}, '
        'I’ll keep my delivery {mood_meaning}. You chose {presence}: {presence_meaning}. Enjoy your session!',
        ('warm, curious company', 'your host with a clear thread to the story',
         'your concise host with a dry sense of humour', 'your playful, welcoming host'),
        ('unhurried and spacious', 'relaxed and flowing', 'bright and brisk', 'lively and playful'),
        ('Music only', 'Occasional', 'Balanced', 'Presenter'),
        ('apart from this welcome, this setting leaves out automatic DJ contributions; your questions are still welcome',
         'I’ll join you with a contribution now and then',
         'I’ll balance contributions with space for the music', 'there is more room for me to join in')),
    'nl': (
        'Jouw DJ-sessie', 'Welkom, fijn dat je er bent! Ik ben je {persona}: {persona_meaning}. '
        'Met {mood} houd ik mijn bijdragen {mood_meaning}. Je koos {presence}: {presence_meaning}. Veel luisterplezier!',
        ('warm en nieuwsgierig gezelschap', 'je presentator die een helder verhaal vertelt',
         'je bondige gastheer met droge humor', 'je speelse en gastvrije gastheer'),
        ('rustig, met ruimte om te landen', 'ontspannen en vloeiend', 'levendig en vlot', 'energiek en speels'),
        ('Alleen muziek', 'Af en toe', 'Gebalanceerd', 'Presentator'),
        ('buiten dit welkom voeg ik bij deze instelling geen automatische DJ-bijdragen toe; jouw vragen blijven welkom',
         'ik schuif zo nu en dan aan met een bijdrage', 'ik wissel bijdragen af met ruimte voor de muziek',
         'er is wat meer ruimte voor mij om aan te schuiven')),
    'de': (
        'Deine DJ-Session', 'Willkommen, schön, dass du da bist! Ich bin dein {persona}: {persona_meaning}. '
        'Mit {mood} erzähle ich {mood_meaning}. Du hast {presence} gewählt: {presence_meaning}. Viel Freude beim Hören!',
        ('warme, neugierige Gesellschaft', 'dein Moderator mit einem klaren roten Faden',
         'dein knapper Gastgeber mit trockenem Humor', 'dein verspielter, einladender Gastgeber'),
        ('ruhig und mit Raum zum Nachklingen', 'entspannt und fließend', 'lebhaft und zügig', 'schwungvoll und verspielt'),
        ('Nur Musik', 'Gelegentlich', 'Ausgewogen', 'Moderator'),
        ('außer dieser Begrüßung gibt es bei dieser Einstellung keine automatischen DJ-Beiträge; deine Fragen bleiben willkommen',
         'ich melde mich ab und zu mit einem Beitrag', 'ich halte Beiträge und Raum für die Musik in Balance',
         'es gibt mehr Raum für meine Begleitung')),
    'fr': (
        'Ta session DJ', 'Bienvenue, ravi de t’accueillir ! Je suis ton {persona} : {persona_meaning}. '
        'Avec {mood}, mon récit sera {mood_meaning}. Tu as choisi {presence} : {presence_meaning}. Bonne écoute !',
        ('une présence chaleureuse et curieuse', 'ton animateur qui donne un fil clair au récit',
         'ton hôte concis à l’humour discret', 'ton hôte enjoué et accueillant'),
        ('calme, avec de l’espace pour respirer', 'détendu et fluide', 'vif et alerte', 'dynamique et joueur'),
        ('Musique seule', 'De temps en temps', 'Équilibré', 'Animateur'),
        ('hormis cet accueil, ce réglage exclut les contributions DJ automatiques ; tes questions restent les bienvenues',
         'j’interviens de temps en temps', 'je partage des récits en laissant de la place à la musique',
         'il y a davantage de place pour mon accompagnement')),
    'es': (
        'Tu sesión de DJ', '¡Qué gusto tenerte aquí! Soy tu {persona}: {persona_meaning}. '
        'Con {mood}, mi forma de contar será {mood_meaning}. Has elegido {presence}: {presence_meaning}. ¡Disfruta de la sesión!',
        ('una compañía cálida y curiosa', 'tu presentador con un hilo claro para cada historia',
         'tu anfitrión conciso y de humor seco', 'tu anfitrión alegre y acogedor'),
        ('tranquila y con espacio para respirar', 'relajada y fluida', 'viva y ágil', 'enérgica y juguetona'),
        ('Solo música', 'De vez en cuando', 'Equilibrado', 'Presentador'),
        ('salvo esta bienvenida, esta opción excluye las aportaciones automáticas del DJ; tus preguntas siguen siendo bienvenidas',
         'comparto una aportación de vez en cuando', 'combino historias con espacio para la música',
         'hay más espacio para mi compañía')),
}


@dataclass(frozen=True)
class SessionOpeningContext:
    session_id: str
    mood: str
    persona: str
    presence: str
    locale: str

    def qualified(self):
        return (self.locale in COPY and self.mood in MOODS
                and self.persona in PERSONAS and self.presence in PRESENCES)

    def values(self):
        if not self.qualified():
            raise ValueError('unqualified_session_opening')
        copy = COPY[self.locale]
        pi, mi, fi = PERSONAS.index(self.persona), MOODS.index(self.mood), PRESENCES.index(self.presence)
        return {'persona': PERSONA_NAMES[pi], 'mood': MOOD_NAMES[mi], 'presence': copy[4][fi],
                'persona_meaning': copy[2][pi], 'mood_meaning': copy[3][mi], 'presence_meaning': copy[5][fi]}

    def seed(self):
        return COPY[self.locale][1].format(**self.values())

    def metadata(self):
        return {'purpose': 'session_opening', 'start_mood': self.mood,
                'start_persona': self.persona, 'start_presence': self.presence}

    def matches(self, moment):
        return (self.qualified() and moment.session_id == self.session_id
                and moment.moment_type.value == 'session' and not moment.source_attribution
                and moment.source_fact is None
                and moment.source_references == ('session_direction',)
                and moment.knowledge_intent.intent_type.value == 'session_direction'
                and moment.presentation_intent.dj_persona.value == self.persona
                and moment.presentation_intent.source_session_mood == self.mood
                and dict(moment.generation_metadata).get('context_source') == 'session_direction'
                and dict(moment.generation_metadata).get('validated') == 'true'
                and all(dict(moment.generation_metadata).get(k) == v for k, v in self.metadata().items()))


def opening_context(moment):
    context = getattr(moment, 'session_opening', None)
    return context if type(context) is SessionOpeningContext and context.matches(moment) else None


def admitted_opening(moment):
    context = opening_context(moment)
    if context is None:
        return False
    from .narration_brief import admitted_runtime_text
    return moment.content == context.seed() or admitted_runtime_text(moment)
