"""Authored local forms for existing immutable context anchors only."""

PERSONAS = ("home_dj", "radio_dj", "club_dj", "festival_dj")
FACT_FAMILIES = frozenset({"album_release", "artist_begin", "artist_description"})

# Alternate forms accompany the previously qualified persona form. Dates and
# descriptors are exact substitutions, never translated or inferred here.
EDITION_ALTERNATE = {
    "en": (
        "{s} has this edition dated {d} in Spotify’s catalog.",
        "{d} is the date Spotify lists for this edition of {s}.",
        "Spotify catalog: {d}, this edition of {s}.",
        "Take this edition of {s}: Spotify puts {d} beside it in the catalog.",
    ),
    "nl": (
        "Bij deze uitgave van {s} staat {d} in de Spotify-catalogus.",
        "{d} is de datum die Spotify vermeldt voor deze uitgave van {s}.",
        "Spotify-catalogus: {d}, deze uitgave van {s}.",
        "Neem deze uitgave van {s}: Spotify zet er {d} bij in de catalogus.",
    ),
    "de": (
        "Bei dieser Ausgabe von {s} steht {d} im Spotify-Katalog.",
        "{d} ist das Datum, das Spotify für diese Ausgabe von {s} nennt.",
        "Spotify-Katalog: {d}, diese Ausgabe von {s}.",
        "Nehmen wir diese Ausgabe von {s}: Spotify setzt im Katalog das Datum {d} dazu.",
    ),
    "fr": (
        "Cette édition de l’album « {s} » porte la date {d} dans le catalogue Spotify.",
        "{d} est la date indiquée par Spotify pour cette édition de l’album « {s} ».",
        "Catalogue Spotify : {d}, cette édition de l’album « {s} ».",
        "Prenons cette édition de l’album « {s} » : Spotify y associe la date {d} dans son catalogue.",
    ),
    "es": (
        "Esta edición de {s} lleva la fecha {d} en el catálogo de Spotify.",
        "{d} es la fecha que Spotify indica para esta edición de {s}.",
        "Catálogo de Spotify: {d}, esta edición de {s}.",
        "Tomemos esta edición de {s}: Spotify le asigna la fecha {d} en el catálogo.",
    ),
}
BIRTH_ALTERNATE = {'en': ('{when}, {s} came into the world.',
        '{s}’s birth dates to {d}.',
        'Born {when}: {s}.',
        '{s} was born {when}.'),
 'nl': ('{when} kwam {s} ter wereld.',
        'De geboorte van {s} dateert van {d}.',
        'Geboren {when}: {s}.',
        '{s} kwam {when} ter wereld.'),
 'de': ('{when} kam {s} zur Welt.',
        'Geboren wurde {s} {when}.',
        'Geboren {when}: {s}.',
        '{s} kam {when} zur Welt.'),
 'fr': ('{when}, {s} vient au monde.',
        'Pour « {s} », la naissance a eu lieu {when}.',
        'Naissance de {s} : {d}.',
        '{s} voit le jour {when}.'),
 'es': ('{when}, {s} vino al mundo.',
        'El nacimiento de {s} tuvo lugar {when}.',
        'Nacimiento de {s}: {d}.',
        '{s} vino al mundo {when}.')}
FORMATION_ALTERNATE = {'en': ('{when}, {s} came together as a group.',
        '{s}’s formation as a group dates to {d}.',
        'Formed {when}: {s}.',
        '{s} began as a group {when}.'),
 'nl': ('{when} ontstond {s} als groep.',
        'De oprichting van {s} als groep dateert van {d}.',
        'Opgericht {when}: {s}.',
        '{s} begon {when} als groep.'),
 'de': ('{when} entstand {s} als Gruppe.',
        'Gegründet wurde {s} {when}.',
        'Gegründet {when}: {s}.',
        'Die Gruppe {s} wurde {when} gegründet.'),
 'fr': ('{when}, {s} se constitue en groupe.',
        'Le groupe « {s} » s’est formé {when}.',
        'Formation de {s} : {d}.',
        'Le groupe {s} se forme {when}.'),
 'es': ('{when}, {s} se constituyó como grupo.',
        'El grupo {s} se formó {when}.',
        'Formación de {s}: {d}.',
        'El grupo {s} se formó {when}.')}
DESCRIPTION_ALTERNATE = {'en': ('Wikidata’s words for {s} are “{d}”; a small introduction to the artist.',
        'Wikidata introduces {s} with “{d}”.',
        'Wikidata on {s}: “{d}”.',
        'A name to put to those words: {s}, “{d}” according to Wikidata.'),
 'nl': ('Wikidata noemt {s} “{d}”; een kleine kennismaking met de artiest.',
        'Wikidata introduceert {s} met “{d}”.',
        'Wikidata over {s}: “{d}”.',
        'Een naam bij die woorden: {s}, “{d}” volgens Wikidata.'),
 'de': ('Wikidata nennt {s} „{d}“; ein kleiner Einstieg zu diesem Namen.',
        'Wikidata stellt {s} mit „{d}“ vor.',
        'Wikidata über {s}: „{d}“.',
        'Ein Name zu diesen Worten: {s}, laut Wikidata „{d}“.'),
 'fr': ('Wikidata dit de {s} : « {d} » ; une petite entrée en matière.',
        'Wikidata présente {s} avec ces mots : « {d} ».',
        'Wikidata sur {s} : « {d} ».',
        'Un nom pour ces mots : {s}, « {d} » selon Wikidata.'),
 'es': ('Wikidata dice de {s}: «{d}»; una pequeña presentación.',
        'Wikidata presenta a {s} con «{d}».',
        'Wikidata sobre {s}: «{d}».',
        'Un nombre para esas palabras: {s}, «{d}» según Wikidata.')}

# Genre means only the existing selected metadata context for this track.
# Two forms per persona, with no musical properties or invented relationship.
ARTIST_GENRE = {'en': (('With {t} playing, a little about {a}: Spotify includes {g} among this artist’s genres.',
         'Spotify links {a} with {g}. Here, the artist is playing with {t}.'),
        ('From {a}, this is {t}. Spotify lists {g} among the artist’s genres.',
         '{t}, by {a}; {g} is one of the artist’s genres on Spotify.'),
        ('{a}, {t}. Artist genre on Spotify: {g}.', '{t} — {a}. Spotify lists the artist under {g}.'),
        ('Meet {a} through {t}: Spotify places the artist among {g} acts.',
         '{a} is in focus with {t}. Spotify also links this artist with {g}.')),
 'nl': (('Terwijl {t} speelt, iets over {a}: Spotify noemt {g} bij de genres van deze artiest.',
         'Spotify verbindt {a} met {g}. Hier klinkt de artiest met {t}.'),
        ('Van {a} hoor je {t}. Spotify noemt {g} bij de genres van de artiest.',
         '{t}, van {a}; {g} is een van de artiestgenres op Spotify.'),
        ('{a}, {t}. Artiestgenre op Spotify: {g}.', '{t} — {a}. Spotify deelt de artiest in bij {g}.'),
        ('Maak kennis met {a} via {t}: Spotify plaatst de artiest bij {g}.',
         '{a} staat in beeld met {t}. Spotify verbindt deze artiest ook met {g}.')),
 'de': (('Während {t} läuft, etwas zu {a}: Spotify nennt {g} unter den Genres dieses Künstlers.',
         'Spotify verbindet {a} mit {g}. Hier läuft {t} von diesem Künstler.'),
        ('Von {a} läuft {t}. Spotify führt {g} unter den Genres des Künstlers.',
         '{t}, von {a}; {g} ist eines der Künstlergenres bei Spotify.'),
        ('{a}, {t}. Künstlergenre bei Spotify: {g}.', '{t} — {a}. Spotify ordnet den Künstler unter {g} ein.'),
        ('Lernen wir {a} mit {t} kennen: Spotify ordnet den Künstler {g} zu.',
         '{a} steht mit {t} im Blickpunkt. Spotify verbindet diesen Künstler auch mit {g}.')),
 'fr': (('Pendant que le titre « {t} » passe, un mot sur {a} : Spotify cite {g} parmi les genres de cet artiste.',
         'Spotify associe {a} à {g}. Ici, cet artiste joue avec le titre {t}.'),
        ('Avec {a}, voici {t}. Spotify cite {g} parmi les genres de l’artiste.',
         '{t}, par {a} ; {g} est un des genres de l’artiste sur Spotify.'),
        ('{a}, {t}. Genre de l’artiste sur Spotify : {g}.', '{t} — {a}. Spotify classe l’artiste sous {g}.'),
        ('Découvrons {a} avec {t} : Spotify associe cet artiste au genre « {g} ».',
         '{a} est à l’affiche avec {t}. Spotify associe aussi cet artiste à {g}.')),
 'es': (('Mientras suena {t}, algo sobre {a}: Spotify incluye {g} entre los géneros de este artista.',
         'Spotify vincula a {a} con {g}. Aquí suena este artista con {t}.'),
        ('De {a}, suena {t}. Spotify incluye {g} entre los géneros del artista.',
         '{t}, de {a}; {g} es uno de los géneros del artista en Spotify.'),
        ('{a}, {t}. Género del artista en Spotify: {g}.', '{t} — {a}. Spotify clasifica al artista en {g}.'),
        ('Conozcamos a {a} con {t}: Spotify sitúa al artista en {g}.',
         '{a} está en primer plano con {t}. Spotify también vincula a este artista con {g}.'))}


GENRE = {'en': (('Let’s look at the genre context of {t} by {a}: {g}.', '{a}, with {t}: the genre context here is {g}.'),
        ('For {t} by {a}, the genre context is {g}.', '{g} is the genre context attached to {t} by {a}.'),
        ('{t} — {a}. Genre context: {g}.', 'Genre context, {g}; the track is {t} by {a}.'),
        ('A glance at {t} by {a}: {g} is its genre context.',
         '{g} is on the genre-context line; the track is {t} by {a}.')),
 'nl': (('Even kijken: bij {t} van {a} hoort de genrecontext {g}.', '{a}, met {t}: de genrecontext hier is {g}.'),
        ('Bij {t} van {a} is de genrecontext {g}.', '{g} is de genrecontext die bij {t} van {a} staat.'),
        ('{t} — {a}. Genrecontext: {g}.', 'Genrecontext, {g}; het nummer is {t} van {a}.'),
        ('Een blik op {t} van {a}: {g} is de genrecontext.',
         '{g} staat bij de genrecontext; het gaat om {t} van {a}.')),
 'de': (('Bei „{t}“ von {a} schauen wir auf den Genrekontext: {g}.',
         '{a}, mit {t}: der Genrekontext hier ist {g}.'),
        ('Bei {t} von {a} ist der Genrekontext {g}.', '{g} ist der Genrekontext, der bei {t} von {a} steht.'),
        ('{t} — {a}. Genrekontext: {g}.', 'Genrekontext, {g}; der Titel ist {t} von {a}.'),
        ('Ein Blick auf {t} von {a}: {g} ist der Genrekontext.',
         '{g} steht beim Genrekontext; es geht um den Titel {t} von {a}.')),
 'fr': (('Regardons le contexte de genre du titre « {t} » de {a} : {g}.',
         '{a}, avec {t} : le contexte de genre ici est {g}.'),
        ('Pour le titre « {t} » de {a}, le contexte de genre est {g}.',
         '{g} est le contexte de genre associé à {t} par {a}.'),
        ('{t} — {a}. Contexte de genre : {g}.', 'Contexte de genre, {g} ; le titre est {t} par {a}.'),
        ('Un regard sur {t} par {a} : {g} est son contexte de genre.',
         '{g} figure dans le contexte de genre ; il s’agit du titre « {t} » de {a}.')),
 'es': (('Miremos el contexto de género de {t} de {a}: {g}.', '{a}, con {t}: el contexto de género aquí es {g}.'),
        ('Para {t} de {a}, el contexto de género es {g}.', '{g} es el contexto de género asociado a {t} de {a}.'),
        ('{t} — {a}. Contexto de género: {g}.', 'Contexto de género, {g}; la canción es {t} de {a}.'),
        ('Una mirada a {t} de {a}: {g} es su contexto de género.',
         '{g} figura en el contexto de género; se trata de {t} de {a}.'))}


def form_count(family: str) -> int:
    """Keep existing credits/callback four-form sequencing intact."""
    return 1 if family == "work_composers" else 2 if family in FACT_FAMILIES | {"genre_context", "album_continuity", "playback_announcement"} else 4


PLAYBACK = {'en': (('For this moment, {title} by {artist} is playing.', 'Here is the music for now: {artist}, with {title}.'),
        ('Now playing: {title}, by {artist}.', '{artist} is on now, with {title}.'),
        ('{artist}. {title}. Playing now.', 'Playing now: {title}. {artist}.'),
        ('The spotlight is on {artist} now, with {title}.', '{title} is playing now; a moment for {artist}.')),
 'nl': (('Er speelt nu {title} van {artist}.', 'Dit is de muziek van nu: {artist}, met {title}.'),
        ('Op dit moment speelt {title}, van {artist}.', '{artist} is nu aan de beurt, met {title}.'),
        ('{artist}. {title}. Speelt nu.', 'Nu speelt: {title}. {artist}.'),
        ('{artist} staat nu centraal, met {title}.', '{title} speelt nu; even aandacht voor {artist}.')),
 'de': (('Für diesen Moment läuft {title} von {artist}.', 'Die Musik für jetzt: {artist}, mit {title}.'),
        ('Jetzt läuft {title}, von {artist}.', 'Zu hören ist jetzt {artist}, mit {title}.'),
        ('{artist}. {title}. Läuft jetzt.', 'Jetzt läuft: {title}. {artist}.'),
        ('Im Mittelpunkt steht jetzt {artist}, mit {title}.', '{title} läuft jetzt; ein Moment für {artist}.')),
 'fr': (('Pour ce moment, c’est {title} par {artist} qui passe.',
         'La musique du moment : {artist}, avec {title}.'),
        ('En ce moment : {title}, par {artist}.', '{artist} passe en ce moment, avec {title}.'),
        ('{artist}. En ce moment : {title}.', 'En ce moment : {title}. {artist}.'),
        ('Place à {artist} en ce moment, avec {title}.',
         '{title} passe en ce moment ; un instant pour {artist}.')),
 'es': (('En este momento suena {title} de {artist}.', 'La música de ahora: {artist}, con {title}.'),
        ('Ahora está sonando {title}, de {artist}.', '{artist} suena ahora, con {title}.'),
        ('{artist}. {title}. Sonando ahora.', 'Ahora suena: {title}. {artist}.'),
        ('El foco está ahora en {artist}, con {title}.', 'Ahora suena {title}; un momento para {artist}.'))}


def playback_copy(*, locale: str, persona: str, form: int, title: str, artist: str) -> str:
    """Two published-only authored forms; exact confirmed metadata, no inference."""
    return PLAYBACK[locale][PERSONAS.index(persona)][form % 2].format(title=title, artist=artist)


GENRE_TRANSITION = {'en': ('Earlier we had {source_track}; now {target_track}. Both are by {artist}, whose Spotify genres include '
        '{genre}.',
        'From {source_track} to {target_track}, the artist stays {artist}. Spotify links this artist with '
        '{genre}.',
        '{artist}: earlier {source_track}, now {target_track}. Spotify lists the artist under {genre}.',
        'Two recordings, one artist: {artist}. After {source_track}, now {target_track}; Spotify places the '
        'artist among {genre} acts.'),
 'nl': ('Eerder klonk {source_track}, nu {target_track}. Beide zijn van {artist}, bij wie Spotify {genre} als '
        'genre noemt.',
        'Van {source_track} naar {target_track}: de artiest blijft {artist}. Spotify verbindt deze artiest met '
        '{genre}.',
        '{artist}: eerder {source_track}, nu {target_track}. Spotify deelt de artiest in bij {genre}.',
        'Twee opnamen, één artiest: {artist}. Na {source_track} klinkt nu {target_track}; Spotify plaatst de '
        'artiest bij {genre}.'),
 'de': ('Zuvor lief {source_track}, jetzt {target_track}. Beide stammen von {artist}; Spotify nennt {genre} unter '
        'den Genres dieses Künstlers.',
        'Von {source_track} zu {target_track}: Der Künstler bleibt {artist}. Spotify verbindet diesen Künstler '
        'mit {genre}.',
        '{artist}: zuvor {source_track}, jetzt {target_track}. Spotify ordnet den Künstler unter {genre} ein.',
        'Zwei Aufnahmen, ein Künstler: {artist}. Nach {source_track} läuft jetzt {target_track}; Spotify ordnet '
        'den Künstler {genre} zu.'),
 'fr': ('Nous avions {source_track}, maintenant {target_track}. Ces deux titres ont pour artiste {artist} ; '
        'Spotify cite {genre} parmi ses genres.',
        'De {source_track} à {target_track}, l’artiste reste {artist}. Spotify associe cet artiste au genre « '
        '{genre} ».',
        '{artist} : auparavant {source_track}, maintenant {target_track}. Spotify classe l’artiste sous le genre '
        '« {genre} ».',
        'Deux enregistrements, un artiste : {artist}. Après {source_track}, voici {target_track} ; Spotify '
        'associe cet artiste au genre « {genre} ».'),
 'es': ('Antes sonó {source_track}, ahora {target_track}. Ambos son de {artist}, cuyo catálogo de géneros en '
        'Spotify incluye {genre}.',
        'De {source_track} a {target_track}, el artista sigue siendo {artist}. Spotify vincula a este artista con '
        '{genre}.',
        '{artist}: antes {source_track}, ahora {target_track}. Spotify clasifica al artista en {genre}.',
        'Dos grabaciones, un artista: {artist}. Tras {source_track}, ahora suena {target_track}; Spotify sitúa al '
        'artista en {genre}.')}
SUGGESTED_TRANSITION = {
    'en': ('A possible connection to consider: from {source} to {target}.', 'The proposed connection runs from {source} to {target}.',
           'Suggested connection: {source} to {target}.', 'A place to explore: the proposed link from {source} to {target}.'),
    'nl': ('Een mogelijk verband om bij stil te staan: van {source} naar {target}.', 'Het voorgestelde verband loopt van {source} naar {target}.',
           'Voorgesteld verband: {source} naar {target}.', 'Een aanknopingspunt om te verkennen: het voorgestelde verband van {source} naar {target}.'),
    'de': ('Eine mögliche Verbindung zum Nachdenken: von {source} zu {target}.', 'Die vorgeschlagene Verbindung führt von {source} zu {target}.',
           'Vorgeschlagene Verbindung: {source} zu {target}.', 'Ein Anhaltspunkt zum Erkunden: die vorgeschlagene Verbindung von {source} zu {target}.'),
    'fr': ('Un lien possible à envisager : de {source} à {target}.', 'Le lien proposé va de {source} à {target}.',
           'Lien proposé : de {source} à {target}.', 'Un point à explorer : le lien proposé de {source} à {target}.'),
    'es': ('Una posible conexión para considerar: de {source} a {target}.', 'La conexión propuesta va de {source} a {target}.',
           'Conexión propuesta: de {source} a {target}.', 'Un punto para explorar: la conexión propuesta de {source} a {target}.'),
}


def transition_copy(*, locale: str, persona: str, context: dict, relation: str) -> str:
    forms = GENRE_TRANSITION if relation == 'discover_same_artist_genre' else SUGGESTED_TRANSITION
    return forms[locale][PERSONAS.index(persona)].format(**context)


def genre_copy(
    *, locale: str, persona: str, form: int, genre: str, title: str, artist: str,
    qualified_artist: bool = False
) -> str | None:
    lang = locale[:2].lower()
    if lang not in GENRE or persona not in PERSONAS:
        return None
    if any(
        not isinstance(v, str)
        or not v
        or len(v) > 160
        or any(ord(c) < 32 or ord(c) == 127 for c in v)
        for v in (genre, title, artist)
    ):
        return None
    forms = ARTIST_GENRE if qualified_artist else GENRE
    return forms[lang][PERSONAS.index(persona)][form % 2].format(g=genre, t=title, a=artist)


MONTHS = {
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
    "nl": ("januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"),
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
}


def human_date(value: str, precision: str, locale: str) -> str | None:
    """Present the qualified date only; never fill unknown month/day values."""
    from .session_facts import qualified_date

    lang = locale.split("-", 1)[0].lower()
    if lang not in MONTHS or not qualified_date(value, precision):
        return None
    if precision == "year":
        return value
    year, month, *days = value.split("-")
    name = MONTHS[lang][int(month) - 1]
    if precision == "month":
        return f"{name} de {year}" if lang == "es" else f"{name} {year}"
    day = int(days[0])
    if lang == "de":
        return f"{day}. {name} {year}"
    if lang == "es":
        return f"{day} de {name} de {year}"
    if lang == "fr" and day == 1:
        return f"1er {name} {year}"
    return f"{day} {name} {year}"


def date_phrase(value: str, precision: str, locale: str) -> str | None:
    """A grammatical birth/formation date phrase, without numeric enum logic."""
    date = human_date(value, precision, locale)
    lang = locale.split("-", 1)[0].lower()
    if date is None:
        return None
    if lang == "de":
        return ("am " if precision == "day" else "im Jahr " if precision == "year" else "im ") + date
    prefixes = {"en": ("on ", "in "), "nl": ("op ", "in "), "fr": ("le ", "en "), "es": ("el ", "en ")}
    return prefixes[lang][precision != "day"] + date
