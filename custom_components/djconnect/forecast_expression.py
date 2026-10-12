"""Authored Forecast presentation of Planner semantics, never planning or AI."""
from __future__ import annotations

COPY = {'en': {'titles': ('Now', 'The coming minutes', 'What I am aiming for'),
        'current': 'Now playing: {title} — {artist}.',
        'empty': 'There is not enough current musical context for a grounded preview yet.',
        'quiet': 'I will leave room for the music. The direction remains visible here while unsolicited DJ '
                 'contributions stay quiet.',
        'chill': 'The aim is breathing room and a gentler pace, with room for the current music to unfold.',
        'groove': 'The aim is a steady flow that can carry the current musical thread without rushing it.',
        'energy': 'The aim is a livelier atmosphere, with the current music as the point of departure.',
        'party': 'The aim is a celebratory atmosphere, keeping the music at the centre.'},
 'nl': {'titles': ('Nu', 'De komende minuten', 'Waar ik op mik'),
        'current': 'Nu speelt: {title} — {artist}.',
        'empty': 'Er is nog te weinig actuele muziekcontext voor een onderbouwde vooruitblik.',
        'quiet': 'Ik geef de muziek de ruimte. De richting blijft hier zichtbaar terwijl ongevraagde DJ-bijdragen '
                 'stil blijven.',
        'chill': 'Het doel is meer ademruimte en een rustiger tempo, zodat de huidige muziek zich kan ontvouwen.',
        'groove': 'Het doel is een gelijkmatige flow die de huidige muzikale draad zonder haast kan dragen.',
        'energy': 'Het doel is een levendiger sfeer, met de huidige muziek als vertrekpunt.',
        'party': 'Het doel is een feestelijke sfeer, met de muziek centraal.'},
 'de': {'titles': ('Jetzt', 'Die nächsten Minuten', 'Worauf ich abziele'),
        'current': 'Jetzt spielt: {title} — {artist}.',
        'empty': 'Für einen fundierten Ausblick fehlt noch genügend aktueller Musikkontext.',
        'quiet': 'Ich lasse der Musik Raum. Die Richtung bleibt hier sichtbar, während ungefragte DJ-Beiträge '
                 'ausbleiben.',
        'chill': 'Das Ziel ist mehr Freiraum und ein sanfteres Tempo, damit sich die aktuelle Musik entfalten '
                 'kann.',
        'groove': 'Das Ziel ist ein gleichmäßiger Fluss, der den aktuellen musikalischen Faden ohne Eile trägt.',
        'energy': 'Das Ziel ist eine lebhaftere Atmosphäre mit der aktuellen Musik als Ausgangspunkt.',
        'party': 'Das Ziel ist eine festliche Atmosphäre, mit der Musik im Mittelpunkt.'},
 'fr': {'titles': ('Maintenant', 'Les prochaines minutes', 'Ce que je vise'),
        'current': 'En ce moment : {title} — {artist}.',
        'empty': 'Le contexte musical actuel est encore trop limité pour un aperçu étayé.',
        'quiet': 'Je laisse de la place à la musique. La direction reste visible ici, tandis que les '
                 'interventions spontanées du DJ restent silencieuses.',
        'chill': 'L’objectif est de laisser respirer la musique et d’adopter un rythme plus doux.',
        'groove': 'L’objectif est un mouvement régulier qui prolonge le fil musical actuel sans le presser.',
        'energy': 'L’objectif est une ambiance plus vive, avec la musique actuelle comme point de départ.',
        'party': 'L’objectif est une ambiance festive, avec la musique au centre.'},
 'es': {'titles': ('Ahora', 'Los próximos minutos', 'Lo que busco'),
        'current': 'Ahora suena: {title} — {artist}.',
        'empty': 'Todavía falta contexto musical actual para ofrecer un avance fundamentado.',
        'quiet': 'Dejo espacio a la música. La dirección sigue visible aquí, mientras las intervenciones '
                 'espontáneas del DJ permanecen en silencio.',
        'chill': 'El objetivo es dar más espacio y un ritmo más suave para que la música actual se desarrolle.',
        'groove': 'El objetivo es un flujo constante que sostenga el hilo musical actual sin apresurarlo.',
        'energy': 'El objetivo es un ambiente más vivo, con la música actual como punto de partida.',
        'party': 'El objetivo es un ambiente festivo, con la música en el centro.'}}

INTENT_FORMS = {'en': {'exploring': ('Around {artist}, I can look for a useful connection when reliable context offers one.',
                      'Starting from {artist}, I can bring a sourced connection into focus when it fits the '
                      'music.',
                      'Space for the music first; a short connection around {artist} can follow if the context '
                      'supports it.',
                      'With {artist} as the anchor, I can share a clear connection if a suitable, sourced opening '
                      'arrives.'),
        'deepening': ('Around {album}, I can linger on a reliable detail if there is room for it.',
                      'The focus can stay on {album}: one sourced detail, when the music allows.',
                      'Let {album} breathe; a brief, reliable detail can fit when there is room.',
                      'A clear detail about {album} can give this stretch a point of focus, if it fits.'),
        'building_energy': ('I have more momentum in mind, with a little context when it suits the music.',
                            'The intention is to build momentum; brief, sourced links can support that direction.',
                            'More momentum is the aim. Any contribution stays short and tied to what actually '
                            'plays.',
                            'I am aiming for more momentum, with a clear musical anchor whenever a contribution '
                            'fits.'),
        'cooling_down': ('I have a calmer atmosphere in mind, with room for the music and an occasional reliable '
                         'detail.',
                         'The intention is a calmer atmosphere; a sourced detail can accompany it when '
                         'appropriate.',
                         'Space first, with a calmer atmosphere as the aim; any detail stays brief and grounded.',
                         'A calmer atmosphere is the goal. I can add a clear detail when there is a suitable '
                         'opening.'),
        'maintaining_energy': ('I can keep a steady thread around {artist}, adding context when it helps.',
                               'A steady musical thread is the intention, with sourced context around {artist} '
                               'when useful.',
                               'Keep the thread steady: room for {artist}, with a short detail only if it adds '
                               'something.',
                               'The aim is a steady thread, with {artist} as the anchor and a clear detail when '
                               'it fits.'),
        'returning': ('I can pick the thread back up when the current music offers a reliable connection.',
                      'A return to the thread can take shape through a sourced connection, if the music offers '
                      'one.',
                      'Back to the thread, when there is a grounded connection; the music keeps its space.',
                      'I can make the thread clear again if the current music provides a suitable, sourced '
                      'opening.'),
        'resetting': ('The music playing now can give us a fresh point of focus.',
                      'A fresh focus can start with the music playing now, with context when it is available.',
                      'A fresh focus, starting here with the music; any context stays brief.',
                      'I can mark a fresh point of focus from the music playing now, when a contribution fits.')},
 'nl': {'exploring': ('Rond {artist} kan ik een mooi verband uitlichten, als betrouwbare context daar aanleiding '
                      'toe geeft.',
                      'Vanuit {artist} kan ik een verband met bronvermelding belichten wanneer het bij de muziek '
                      'past.',
                      'Eerst ruimte voor de muziek; een kort verband rond {artist} kan volgen als de context het '
                      'draagt.',
                      'Met {artist} als anker kan ik een helder verband delen zodra zich een passende, '
                      'onderbouwde kans voordoet.'),
        'deepening': ('Rond {album} kan ik een betrouwbaar detail uitlichten, als daar ruimte voor is.',
                      'De aandacht kan bij {album} blijven: één detail met bronvermelding, wanneer het past.',
                      'Laat {album} ademen; een kort, betrouwbaar detail kan erbij als er ruimte is.',
                      'Een helder detail over {album} kan dit deel een aanknopingspunt geven, als het past.'),
        'building_energy': ('Ik heb meer vaart voor ogen, met wat context wanneer de muziek daar ruimte voor '
                            'geeft.',
                            'Het voornemen is meer vaart, met korte verbanden uit betrouwbare bronnen als '
                            'ondersteuning.',
                            'Meer vaart is het doel. Een bijdrage blijft kort en hoort bij wat werkelijk speelt.',
                            'Ik mik op meer vaart, met een helder muzikaal anker wanneer een bijdrage past.'),
        'cooling_down': ('Ik heb een rustiger sfeer voor ogen, met ruimte voor de muziek en af en toe een '
                         'betrouwbaar detail.',
                         'Het voornemen is een rustiger sfeer; een detail met bronvermelding kan die begeleiden '
                         'wanneer het past.',
                         'Eerst ruimte, met rust als doel; een detail blijft kort en onderbouwd.',
                         'Een rustiger sfeer is het doel. Ik kan een helder detail toevoegen zodra daar ruimte '
                         'voor is.'),
        'maintaining_energy': ('Ik kan de draad rond {artist} gelijkmatig houden en context toevoegen wanneer die '
                               'helpt.',
                               'Een gelijkmatige muzikale draad is het voornemen, met broncontext rond {artist} '
                               'wanneer die iets toevoegt.',
                               'De draad gelijkmatig houden: ruimte voor {artist}, met alleen een kort detail als '
                               'dat iets toevoegt.',
                               'Het doel is een gelijkmatige draad, met {artist} als anker en een helder detail '
                               'wanneer het past.'),
        'returning': ('Ik kan de draad weer oppakken wanneer de muziek een betrouwbaar verband biedt.',
                      'De draad kan terugkomen via een onderbouwd verband, als de muziek daar aanleiding toe '
                      'geeft.',
                      'Terug naar de draad wanneer er een onderbouwd verband is; de muziek houdt de ruimte.',
                      'Ik kan de draad weer helder maken als de muziek een passende, onderbouwde opening biedt.'),
        'resetting': ('De muziek die nu speelt kan een nieuw aanknopingspunt geven.',
                      'Een nieuw aanknopingspunt kan beginnen bij de muziek die nu speelt, met context zodra die '
                      'beschikbaar is.',
                      'Een nieuw aanknopingspunt, hier bij de muziek; eventuele context blijft kort.',
                      'Ik kan vanuit de muziek die nu speelt een nieuw aanknopingspunt markeren wanneer een '
                      'bijdrage past.')},
 'de': {'exploring': ('Rund um {artist} kann ich eine Verbindung aufgreifen, wenn verlässlicher Kontext sie '
                      'trägt.',
                      'Ausgehend von {artist} kann ich eine belegte Verbindung beleuchten, wenn sie zur Musik '
                      'passt.',
                      'Zuerst Raum für die Musik; eine kurze Verbindung zu {artist} kann folgen, wenn der Kontext '
                      'stimmt.',
                      'Mit {artist} als Anker kann ich eine klare Verbindung teilen, wenn sich eine belegte '
                      'Gelegenheit bietet.'),
        'deepening': ('Rund um {album} kann ich bei einem verlässlichen Detail verweilen, wenn dafür Raum ist.',
                      'Der Fokus kann bei {album} bleiben: ein belegtes Detail, wenn es zur Musik passt.',
                      '{album} darf atmen; ein kurzes, verlässliches Detail kann dazukommen, wenn Raum bleibt.',
                      'Ein klares Detail zu {album} kann diesem Abschnitt einen Bezugspunkt geben, wenn es '
                      'passt.'),
        'building_energy': ('Ich habe mehr Schwung im Sinn, mit etwas Kontext, wenn die Musik dafür Raum lässt.',
                            'Mehr Schwung ist die Absicht; kurze, belegte Verbindungen können diese Richtung '
                            'begleiten.',
                            'Mehr Schwung ist das Ziel. Jeder Beitrag bleibt kurz und an die tatsächlich '
                            'spielende Musik gebunden.',
                            'Ich ziele auf mehr Schwung, mit einem klaren musikalischen Anker, wenn ein Beitrag '
                            'passt.'),
        'cooling_down': ('Ich habe eine ruhigere Atmosphäre im Sinn, mit Raum für die Musik und gelegentlich '
                         'einem verlässlichen Detail.',
                         'Die Absicht ist eine ruhigere Atmosphäre; ein belegtes Detail kann sie begleiten, wenn '
                         'es passt.',
                         'Raum zuerst, mit einer ruhigeren Atmosphäre als Ziel; jedes Detail bleibt kurz und '
                         'fundiert.',
                         'Eine ruhigere Atmosphäre ist das Ziel. Ein klares Detail kann hinzukommen, wenn sich '
                         'Raum bietet.'),
        'maintaining_energy': ('Ich kann den Faden um {artist} gleichmäßig halten und Kontext ergänzen, wenn er '
                               'hilft.',
                               'Ein gleichmäßiger musikalischer Faden ist die Absicht, mit belegtem Kontext zu '
                               '{artist}, wenn er nützt.',
                               'Den Faden ruhig halten: Raum für {artist}, ein kurzes Detail nur mit Mehrwert.',
                               'Das Ziel ist ein gleichmäßiger Faden, mit {artist} als Anker und einem klaren '
                               'Detail, wenn es passt.'),
        'returning': ('Ich kann den Faden wieder aufnehmen, wenn die Musik eine verlässliche Verbindung bietet.',
                      'Der Faden kann durch eine belegte Verbindung zurückkehren, wenn die Musik sie ermöglicht.',
                      'Zurück zum Faden, wenn eine fundierte Verbindung da ist; die Musik behält ihren Raum.',
                      'Ich kann den Faden wieder sichtbar machen, wenn die Musik eine passende, belegte '
                      'Gelegenheit bietet.'),
        'resetting': ('Die Musik, die jetzt spielt, kann einen neuen Bezugspunkt geben.',
                      'Ein neuer Fokus kann bei der Musik beginnen, die jetzt spielt, mit Kontext, sobald er '
                      'verfügbar ist.',
                      'Ein neuer Fokus, hier bei der Musik; möglicher Kontext bleibt kurz.',
                      'Ich kann aus der jetzt spielenden Musik einen neuen Bezugspunkt machen, wenn ein Beitrag '
                      'passt.')},
 'fr': {'exploring': ('Autour de {artist}, je peux éclairer un lien lorsque des informations fiables le '
                      'permettent.',
                      'À partir de {artist}, je peux mettre un lien sourcé en lumière lorsqu’il convient à la '
                      'musique.',
                      'La musique garde sa place ; un bref lien autour de {artist} peut suivre si le contexte le '
                      'justifie.',
                      'Avec {artist} comme repère, je peux partager un lien clair si une occasion étayée se '
                      'présente.'),
        'deepening': ('Autour de {album}, je peux m’attarder sur un détail fiable lorsqu’il y a de la place.',
                      'Le regard peut rester sur {album} : un détail sourcé, lorsque la musique le permet.',
                      'Laissons respirer {album} ; un détail bref et fiable peut trouver sa place lorsque la '
                      'musique le permet.',
                      'Un détail clair sur {album} peut donner un repère à ce passage, si cela convient.'),
        'building_energy': ('J’envisage davantage d’élan, avec un peu de contexte lorsque la musique lui laisse '
                            'une place.',
                            'L’intention est de donner plus d’élan ; de brefs liens sourcés peuvent accompagner '
                            'cette direction.',
                            'Davantage d’élan est l’objectif. Toute intervention reste brève et liée à ce qui '
                            'joue réellement.',
                            'Je vise davantage d’élan, avec un repère musical clair lorsqu’une intervention '
                            'convient.'),
        'cooling_down': ('J’envisage une ambiance plus calme, avec de la place pour la musique et parfois un '
                         'détail fiable.',
                         'L’intention est une ambiance plus calme ; un détail sourcé peut l’accompagner lorsqu’il '
                         'convient.',
                         'De la place d’abord, avec une ambiance plus calme comme objectif ; chaque détail reste '
                         'bref et étayé.',
                         'Une ambiance plus calme est l’objectif. Je peux ajouter un détail clair lorsqu’une '
                         'occasion se présente.'),
        'maintaining_energy': ('Je peux garder un fil régulier autour de {artist}, avec du contexte lorsqu’il est '
                               'utile.',
                               'Un fil musical régulier est l’intention, avec du contexte sourcé autour de '
                               '{artist} lorsqu’il apporte quelque chose.',
                               'Garder le fil régulier : de la place pour {artist}, un bref détail seulement s’il '
                               'apporte quelque chose.',
                               'L’objectif est un fil régulier, avec {artist} comme repère et un détail clair '
                               'lorsqu’il convient.'),
        'returning': ('Je peux reprendre le fil lorsque la musique offre un lien fiable.',
                      'Le fil peut revenir grâce à un lien sourcé, si la musique en offre l’occasion.',
                      'Retour au fil lorsqu’un lien étayé se présente ; la musique garde sa place.',
                      'Je peux rendre le fil plus clair si la musique offre une occasion adaptée et étayée.'),
        'resetting': ('La musique qui joue maintenant peut offrir un nouveau repère.',
                      'Un nouveau point d’attention peut partir de la musique qui joue maintenant, avec du '
                      'contexte lorsqu’il est disponible.',
                      'Un nouveau repère, ici dans la musique ; tout contexte reste bref.',
                      'Je peux marquer un nouveau repère dans la musique qui joue maintenant lorsqu’une '
                      'intervention convient.')},
 'es': {'exploring': ('En torno a {artist}, puedo destacar una conexión cuando la información fiable lo permita.',
                      'A partir de {artist}, puedo destacar una conexión documentada cuando encaje con la música.',
                      'Primero, espacio para la música; una conexión breve con {artist} puede seguir si el '
                      'contexto la respalda.',
                      'Con {artist} como referencia, puedo compartir una conexión clara si aparece una ocasión '
                      'fundamentada.'),
        'deepening': ('En torno a {album}, puedo detenerme en un detalle fiable si hay espacio para él.',
                      'El foco puede seguir en {album}: un detalle con fuente, cuando la música lo permita.',
                      'Dejemos respirar a {album}; un detalle breve y fiable puede encajar cuando haya espacio.',
                      'Un detalle claro sobre {album} puede dar una referencia a este tramo, si encaja.'),
        'building_energy': ('Tengo en mente más impulso, con algo de contexto cuando la música le deje espacio.',
                            'La intención es dar más impulso; conexiones breves y fundamentadas pueden acompañar '
                            'esa dirección.',
                            'Más impulso es el objetivo. Cada intervención sigue siendo breve y ligada a lo que '
                            'realmente suena.',
                            'Busco más impulso, con una referencia musical clara cuando encaje una intervención.'),
        'cooling_down': ('Tengo en mente un ambiente más tranquilo, con espacio para la música y algún detalle '
                         'fiable.',
                         'La intención es un ambiente más tranquilo; un detalle con fuente puede acompañarlo '
                         'cuando encaje.',
                         'Espacio primero, con un ambiente más tranquilo como objetivo; cada detalle sigue siendo '
                         'breve y fundamentado.',
                         'Un ambiente más tranquilo es el objetivo. Puedo añadir un detalle claro cuando haya una '
                         'ocasión adecuada.'),
        'maintaining_energy': ('Puedo mantener un hilo constante alrededor de {artist}, con contexto cuando '
                               'ayude.',
                               'Un hilo musical constante es la intención, con contexto fundamentado sobre '
                               '{artist} cuando aporte algo.',
                               'Mantener el hilo constante: espacio para {artist}, un detalle breve solo si '
                               'aporta algo.',
                               'El objetivo es un hilo constante, con {artist} como referencia y un detalle claro '
                               'cuando encaje.'),
        'returning': ('Puedo retomar el hilo cuando la música ofrezca una conexión fiable.',
                      'El hilo puede volver mediante una conexión con fuente, si la música ofrece la ocasión.',
                      'Volver al hilo cuando haya una conexión fundamentada; la música conserva su espacio.',
                      'Puedo aclarar el hilo si la música ofrece una ocasión adecuada y fundamentada.'),
        'resetting': ('La música que suena ahora puede ofrecer una nueva referencia.',
                      'Un nuevo foco puede partir de la música que suena ahora, con contexto cuando esté '
                      'disponible.',
                      'Una nueva referencia, aquí en la música; cualquier contexto sigue siendo breve.',
                      'Puedo marcar una nueva referencia en la música que suena ahora cuando encaje una '
                      'intervención.')}}
PERSONAS = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')


def realize(semantic: dict, locale: str, persona: str) -> tuple[str, list[dict]]:
    """Render only the closed Planner-produced meanings; no inference/lookup."""
    language = locale if locale in COPY else 'en'
    c = COPY[language]
    if not semantic.get('has_current'):
        return c['empty'], []
    values = {k: str(semantic.get(k) or '') for k in ('title', 'artist', 'album')}
    sections = [{'id': 'current', 'title': c['titles'][0], 'claim_type': 'current',
                 'text': c['current'].format(**values), 'source_url': semantic['source_url']}]
    code = semantic['guidance']
    forms = INTENT_FORMS[language].get(code)
    text = forms[PERSONAS.index(persona) if persona in PERSONAS else 0].format(**values) if forms else c.get(code, c['empty'])
    if forms or code == 'quiet':
        sections.append({'id': 'guidance', 'title': c['titles'][1], 'claim_type': 'intention', 'text': text})
    if semantic.get('aim') in ('chill', 'groove', 'energy', 'party'):
        sections.append({'id': 'aim', 'title': c['titles'][2], 'claim_type': 'conditional_target', 'text': c[semantic['aim']]})
    return text, sections
