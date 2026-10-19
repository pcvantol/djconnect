"""Core-owned playful phrasing, with no claimed music facts or model work."""
from __future__ import annotations

KINDS = ('check_in', 'playful', 'easter_egg')
LANGUAGES = ('en', 'nl', 'de', 'fr', 'es')
PERSONAS = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')
MOODS = ('chill', 'groove', 'energy', 'party')

# A complete short reaction combines a Persona/kind construction with one of
# two Mood clauses. These are subjective invitations, never listening facts,
# inferred memories or assertions about a track, artist or physical output.
FRAMES = {
    'en': {
        'home_dj': ('A little nod from your DJ: {mood}', 'No extra fuss from me; {mood}', 'Secret handshake accepted; {mood}'),
        'radio_dj': ('A quick word from the booth: {mood}', 'A tiny radio message: {mood}', 'You found the unlisted button; {mood}'),
        'club_dj': ('A small nod, then space: {mood}', 'One tap, very few words: {mood}', 'No secret drop, just this: {mood}'),
        'festival_dj': ('A little wave from the festival booth: {mood}', 'That tap deserves a tiny flourish: {mood}', 'Backstage password accepted; {mood}'),
    },
    'nl': {
        'home_dj': ('Even een knikje van je DJ: {mood}', 'Geen grote toespraak van mij; {mood}', 'Geheime handdruk ontvangen; {mood}'),
        'radio_dj': ('Een kort bericht uit de cabine: {mood}', 'Een piepklein radiobericht: {mood}', 'Je hebt de knop zonder label gevonden; {mood}'),
        'club_dj': ('Kleine knik, verder ruimte: {mood}', 'Eén tik, weinig woorden: {mood}', 'Geen geheime drop, alleen dit: {mood}'),
        'festival_dj': ('Een klein zwaaitje vanuit de festivaltent: {mood}', 'Die tik verdient een kleine buiging: {mood}', 'Backstagewachtwoord geaccepteerd; {mood}'),
    },
    'de': {
        'home_dj': ('Ein kleines Nicken von deinem DJ: {mood}', 'Keine große Ansprache von mir; {mood}', 'Geheimer Handschlag angekommen; {mood}'),
        'radio_dj': ('Eine kurze Meldung aus der Kabine: {mood}', 'Eine winzige Radiomeldung: {mood}', 'Du hast den unbeschrifteten Knopf gefunden; {mood}'),
        'club_dj': ('Ein kleines Nicken, dann wieder Raum: {mood}', 'Ein Tippen, wenige Worte: {mood}', 'Kein geheimer Drop, nur das: {mood}'),
        'festival_dj': ('Ein kleiner Gruß aus dem Festivalzelt: {mood}', 'Das Tippen verdient eine kleine Verbeugung: {mood}', 'Backstage-Passwort akzeptiert; {mood}'),
    },
    'fr': {
        'home_dj': ('Un petit signe de ton DJ : {mood}', 'Pas de grand discours de ma part ; {mood}', 'Poignée de main secrète reçue ; {mood}'),
        'radio_dj': ('Un bref mot depuis la cabine : {mood}', 'Un tout petit message radio : {mood}', 'Tu as trouvé le bouton sans étiquette ; {mood}'),
        'club_dj': ('Un petit signe, puis de l’espace : {mood}', 'Un appui, très peu de mots : {mood}', 'Pas de drop secret, juste ceci : {mood}'),
        'festival_dj': ('Un petit salut depuis la scène du festival : {mood}', 'Cet appui mérite une petite révérence : {mood}', 'Mot de passe des coulisses accepté ; {mood}'),
    },
    'es': {
        'home_dj': ('Un pequeño saludo de tu DJ: {mood}', 'Sin un gran discurso por mi parte; {mood}', 'Saludo secreto recibido; {mood}'),
        'radio_dj': ('Un breve mensaje desde la cabina: {mood}', 'Un pequeño mensaje de radio: {mood}', 'Has encontrado el botón sin etiqueta; {mood}'),
        'club_dj': ('Un pequeño saludo y después espacio: {mood}', 'Un toque, pocas palabras: {mood}', 'Sin un drop secreto, solo esto: {mood}'),
        'festival_dj': ('Un pequeño saludo desde el escenario del festival: {mood}', 'Ese toque merece una pequeña reverencia: {mood}', 'Contraseña de camerinos aceptada; {mood}'),
    },
}
CLAUSES = {
    'en': {
        'chill': ('let’s leave the rush outside.', 'no hurry, there is room to breathe.'),
        'groove': ('let’s give the groove some room.', 'a little swing goes a long way.'),
        'energy': ('let’s put a spring in this.', 'a little extra spark is welcome.'),
        'party': ('let’s make a small celebration of it.', 'imaginary confetti is perfectly allowed.'),
    },
    'nl': {
        'chill': ('we laten de haast lekker buiten.', 'geen haast, er is ruimte om te ademen.'),
        'groove': ('we geven de groove alle ruimte.', 'een beetje swing doet al een hoop.'),
        'energy': ('we mogen best wat vaart maken.', 'een extra vonkje mag er wel bij.'),
        'party': ('hier mag best een klein feestje van komen.', 'denkbeeldige confetti is helemaal toegestaan.'),
    },
    'de': {
        'chill': ('lassen wir die Hektik draußen.', 'keine Eile, hier ist Platz zum Durchatmen.'),
        'groove': ('geben wir dem Groove etwas Raum.', 'ein bisschen Swing bringt schon viel.'),
        'energy': ('bringen wir etwas Schwung hinein.', 'ein zusätzlicher Funke ist willkommen.'),
        'party': ('machen wir eine kleine Feier daraus.', 'imaginäres Konfetti ist ausdrücklich erlaubt.'),
    },
    'fr': {
        'chill': ('laissons la précipitation dehors.', 'rien ne presse, il y a de quoi respirer.'),
        'groove': ('laissons un peu de place au groove.', 'un peu de swing fait déjà beaucoup.'),
        'energy': ('mettons un peu d’élan dans tout ça.', 'une petite étincelle de plus est bienvenue.'),
        'party': ('faisons-en une petite fête.', 'les confettis imaginaires sont tout à fait permis.'),
    },
    'es': {
        'chill': ('dejemos las prisas fuera.', 'sin prisa, hay espacio para respirar.'),
        'groove': ('dejemos espacio al groove.', 'un poco de swing da para mucho.'),
        'energy': ('pongamos un poco de impulso.', 'una chispa más siempre es bienvenida.'),
        'party': ('hagamos una pequeña fiesta de esto.', 'el confeti imaginario está totalmente permitido.'),
    },
}


def render(*, persona, mood, language, kind, sequence):
    """Closed inputs and bounded variation; caller text never enters a template."""
    if (persona not in PERSONAS or mood not in MOODS or language not in LANGUAGES
            or kind not in KINDS or type(sequence) is not int or sequence < 0):
        raise ValueError('invalid_reaction_style')
    return FRAMES[language][persona][KINDS.index(kind)].format(
        mood=CLAUSES[language][mood][sequence % 2])
