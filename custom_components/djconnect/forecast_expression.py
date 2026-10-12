"""Authored Forecast presentation of Planner semantics, never planning or AI."""
from __future__ import annotations

COPY = {
    'en': {
        'titles': ('Now', 'The coming minutes', 'What I am aiming for'),
        'current': '{title} — {artist} is the confirmed starting point.',
        'empty': 'There is not enough current musical context for a grounded preview yet.',
        'quiet': 'I will leave room for the music. The direction remains visible here while unsolicited DJ contributions stay quiet.',
        'exploring': 'With {artist} as the current starting point, I can bring out useful connections when reliable context for the music we actually hear becomes available.',
        'deepening': 'I can stay closer to {album}, giving a verified detail room to land when this session provides one.',
        'building_energy': 'I can accompany the intended rise in momentum with concise contributions tied to the music that actually arrives.',
        'cooling_down': 'I can leave more space around the current music and use a verified detail sparingly as the session settles.',
        'maintaining_energy': 'I can keep the guidance steady, drawing on fresh context around {artist} when there is something useful to add.',
        'returning': 'I can reconnect the thread through current, verified musical context when a suitable opening appears.',
        'resetting': 'I can give this stretch a fresh point of focus, starting from the music now confirmed in the session.',
        'chill': 'The aim is breathing room and a gentler pace, with room for the current music to unfold.',
        'groove': 'The aim is a steady flow that can carry the current musical thread without rushing it.',
        'energy': 'The aim is a livelier atmosphere, with the current music as the point of departure.',
        'party': 'The aim is a celebratory atmosphere, keeping the music at the centre.',
        'persona': ('Here is the direction I have in mind. ', 'On the session horizon: ', 'The thread to carry forward: ', 'The direction for this stretch: '),
    },
    'nl': {
        'titles': ('Nu', 'De komende minuten', 'Waar ik op mik'),
        'current': '{title} — {artist} is het bevestigde vertrekpunt.',
        'empty': 'Er is nog te weinig actuele muziekcontext voor een onderbouwde vooruitblik.',
        'quiet': 'Ik geef de muziek de ruimte. De richting blijft hier zichtbaar terwijl ongevraagde DJ-bijdragen stil blijven.',
        'exploring': 'Met {artist} als huidig vertrekpunt kan ik bruikbare verbanden uitlichten zodra betrouwbare context bij de muziek die we werkelijk horen beschikbaar komt.',
        'deepening': 'Ik kan dichter bij {album} blijven en een bevestigd detail de ruimte geven zodra deze sessie daar aanleiding toe biedt.',
        'building_energy': 'Ik kan de bedoelde opbouw in vaart begeleiden met korte bijdragen bij de muziek die werkelijk voorbij komt.',
        'cooling_down': 'Ik kan meer ruimte rond de huidige muziek laten en een bevestigd detail spaarzaam inzetten terwijl de sessie tot rust komt.',
        'maintaining_energy': 'Ik kan de begeleiding gelijkmatig houden en actuele context rond {artist} gebruiken wanneer die iets toevoegt.',
        'returning': 'Ik kan de draad weer oppakken via actuele, bevestigde muziekcontext zodra zich een passende opening voordoet.',
        'resetting': 'Ik kan dit deel een nieuw aanknopingspunt geven, vanuit de muziek die nu in de sessie bevestigd is.',
        'chill': 'Het doel is meer ademruimte en een rustiger tempo, zodat de huidige muziek zich kan ontvouwen.',
        'groove': 'Het doel is een gelijkmatige flow die de huidige muzikale draad zonder haast kan dragen.',
        'energy': 'Het doel is een levendiger sfeer, met de huidige muziek als vertrekpunt.',
        'party': 'Het doel is een feestelijke sfeer, met de muziek centraal.',
        'persona': ('Dit is de richting die ik voor ogen heb. ', 'Aan de horizon van deze sessie: ', 'De draad om verder te dragen: ', 'De richting voor dit deel: '),
    },
    'de': {
        'titles': ('Jetzt', 'Die nächsten Minuten', 'Worauf ich abziele'),
        'current': '{title} — {artist} ist der bestätigte Ausgangspunkt.',
        'empty': 'Für einen fundierten Ausblick fehlt noch genügend aktueller Musikkontext.',
        'quiet': 'Ich lasse der Musik Raum. Die Richtung bleibt hier sichtbar, während ungefragte DJ-Beiträge ausbleiben.',
        'exploring': 'Mit {artist} als aktuellem Ausgangspunkt kann ich hilfreiche Verbindungen zeigen, sobald verlässlicher Kontext zur tatsächlich gehörten Musik vorliegt.',
        'deepening': 'Ich kann näher bei {album} bleiben und einem bestätigten Detail Raum geben, sobald die Sitzung dafür einen Anlass bietet.',
        'building_energy': 'Ich kann den angestrebten Schwung mit knappen Beiträgen zur Musik begleiten, die tatsächlich ankommt.',
        'cooling_down': 'Ich kann der aktuellen Musik mehr Raum lassen und ein bestätigtes Detail sparsam einsetzen, während die Sitzung ruhiger wird.',
        'maintaining_energy': 'Ich kann die Begleitung gleichmäßig halten und frischen Kontext zu {artist} nutzen, wenn er etwas beiträgt.',
        'returning': 'Ich kann den Faden über aktuellen, bestätigten Musikkontext wieder aufnehmen, sobald sich eine passende Gelegenheit ergibt.',
        'resetting': 'Ich kann diesem Abschnitt einen neuen Schwerpunkt geben, ausgehend von der jetzt bestätigten Musik.',
        'chill': 'Das Ziel ist mehr Freiraum und ein sanfteres Tempo, damit sich die aktuelle Musik entfalten kann.',
        'groove': 'Das Ziel ist ein gleichmäßiger Fluss, der den aktuellen musikalischen Faden ohne Eile trägt.',
        'energy': 'Das Ziel ist eine lebhaftere Atmosphäre mit der aktuell bestätigten Musik als Ausgangspunkt.',
        'party': 'Das Ziel ist eine festliche Atmosphäre, mit der Musik im Mittelpunkt.',
        'persona': ('Diese Richtung habe ich im Blick. ', 'Am Horizont der Sitzung: ', 'Der Faden für den weiteren Verlauf: ', 'Die Richtung für diesen Abschnitt: '),
    },
    'fr': {
        'titles': ('Maintenant', 'Les prochaines minutes', 'Ce que je vise'),
        'current': '{title} — {artist} est le point de départ confirmé.',
        'empty': 'Le contexte musical actuel est encore trop limité pour un aperçu étayé.',
        'quiet': 'Je laisse de la place à la musique. La direction reste visible ici, tandis que les interventions spontanées du DJ restent silencieuses.',
        'exploring': 'À partir de {artist}, je peux mettre en lumière des liens utiles dès qu’un contexte fiable accompagne la musique réellement entendue.',
        'deepening': 'Je peux rester plus près de {album} et laisser un détail vérifié prendre sa place quand la session en donne l’occasion.',
        'building_energy': 'Je peux accompagner l’élan recherché par de brèves interventions liées à la musique qui arrive réellement.',
        'cooling_down': 'Je peux laisser davantage de place à la musique actuelle et évoquer un détail vérifié avec retenue pendant que la session se pose.',
        'maintaining_energy': 'Je peux garder un accompagnement régulier, avec du contexte récent autour de {artist} lorsqu’il apporte quelque chose.',
        'returning': 'Je peux renouer le fil grâce à un contexte musical actuel et vérifié quand une occasion adaptée se présente.',
        'resetting': 'Je peux donner un nouveau point d’appui à ce passage, à partir de la musique actuellement confirmée.',
        'chill': 'L’objectif est de laisser respirer la musique et d’adopter un rythme plus doux.',
        'groove': 'L’objectif est un mouvement régulier qui prolonge le fil musical actuel sans le presser.',
        'energy': 'L’objectif est une ambiance plus vive, avec la musique actuellement confirmée comme point de départ.',
        'party': 'L’objectif est une ambiance festive, avec la musique au centre.',
        'persona': ('Voici la direction que j’envisage. ', 'À l’horizon de cette session : ', 'Le fil à prolonger : ', 'La direction pour ce passage : '),
    },
    'es': {
        'titles': ('Ahora', 'Los próximos minutos', 'Lo que busco'),
        'current': '{title} — {artist} es el punto de partida confirmado.',
        'empty': 'Todavía falta contexto musical actual para ofrecer un avance fundamentado.',
        'quiet': 'Dejo espacio a la música. La dirección sigue visible aquí, mientras las intervenciones espontáneas del DJ permanecen en silencio.',
        'exploring': 'Con {artist} como punto de partida actual, puedo destacar conexiones útiles cuando haya contexto fiable sobre la música que realmente suena.',
        'deepening': 'Puedo quedarme más cerca de {album} y dar espacio a un detalle verificado cuando la sesión lo permita.',
        'building_energy': 'Puedo acompañar el impulso buscado con intervenciones breves sobre la música que realmente llegue.',
        'cooling_down': 'Puedo dejar más espacio a la música actual y mencionar algún detalle verificado con mesura mientras la sesión se calma.',
        'maintaining_energy': 'Puedo mantener una guía constante y usar contexto reciente sobre {artist} cuando aporte algo.',
        'returning': 'Puedo retomar el hilo mediante contexto musical actual y verificado cuando aparezca una ocasión adecuada.',
        'resetting': 'Puedo dar a este tramo un nuevo punto de apoyo, partiendo de la música que ahora está confirmada.',
        'chill': 'El objetivo es dar más espacio y un ritmo más suave para que la música actual se desarrolle.',
        'groove': 'El objetivo es un flujo constante que sostenga el hilo musical actual sin apresurarlo.',
        'energy': 'El objetivo es un ambiente más vivo, con la música actualmente confirmada como punto de partida.',
        'party': 'El objetivo es un ambiente festivo, con la música en el centro.',
        'persona': ('Esta es la dirección que tengo en mente. ', 'En el horizonte de la sesión: ', 'El hilo que podemos continuar: ', 'La dirección para este tramo: '),
    },
}
PERSONAS = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')


def realize(semantic: dict, locale: str, persona: str) -> tuple[str, list[dict]]:
    """Render only the closed Planner-produced meanings; no inference/lookup."""
    c = COPY.get(locale, COPY['en'])
    frame = c['persona'][PERSONAS.index(persona) if persona in PERSONAS else 0]
    if not semantic.get('has_current'):
        return c['empty'], []
    values = {k: str(semantic.get(k) or '') for k in ('title', 'artist', 'album')}
    sections = [{'id': 'current', 'title': c['titles'][0], 'claim_type': 'current',
                 'text': c['current'].format(**values), 'source_url': semantic['source_url']}]
    code = semantic['guidance']
    if code in c:
        sections.append({'id': 'guidance', 'title': c['titles'][1], 'claim_type': 'intention',
                         'text': frame + c[code].format(**values)})
    if semantic.get('aim') in ('chill', 'groove', 'energy', 'party'):
        sections.append({'id': 'aim', 'title': c['titles'][2], 'claim_type': 'conditional_target',
                         'text': c[semantic['aim']]})
    return frame + c[code].format(**values) if code in c else c['empty'], sections
