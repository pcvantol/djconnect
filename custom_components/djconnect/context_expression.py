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
        "Cette édition de {s} porte la date {d} dans le catalogue Spotify.",
        "{d} est la date indiquée par Spotify pour cette édition de {s}.",
        "Catalogue Spotify : {d}, cette édition de {s}.",
        "Prenons cette édition de {s} : Spotify y associe la date {d} dans son catalogue.",
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
        'La naissance de {s} date de {d}.',
        'Naissance de {s} : {d}.',
        '{s} voit le jour {when}.'),
 'es': ('{when}, {s} vino al mundo.',
        'El nacimiento de {s} data de {d}.',
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
        'La formation de {s} en tant que groupe date de {d}.',
        'Formation de {s} : {d}.',
        'Le groupe {s} se forme {when}.'),
 'es': ('{when}, {s} se constituyó como grupo.',
        'La formación de {s} como grupo data de {d}.',
        'Formación de {s}: {d}.',
        'El grupo {s} se formó {when}.')}
DESCRIPTION_ALTERNATE = {
    "en": (
        "{s} appears in the short description as “{d}”.",
        "“{d}”: these are the words of the short description of {s}.",
        "Short description: “{d}”, for {s}.",
        "“{d}”: meet {s} through the short description.",
    ),
    "nl": (
        "{s} staat in de korte beschrijving als “{d}”.",
        "“{d}”: dit zijn de woorden van de korte beschrijving van {s}.",
        "Korte beschrijving: “{d}”, voor {s}.",
        "“{d}”: maak kennis met {s} via de korte beschrijving.",
    ),
    "de": (
        "{s} steht in der Kurzbeschreibung als „{d}“.",
        "„{d}“: so lautet die Kurzbeschreibung von {s}.",
        "Kurzbeschreibung: „{d}“, für {s}.",
        "„{d}“: so lernen wir {s} durch die Kurzbeschreibung kennen.",
    ),
    "fr": (
        "{s} figure dans la courte description ainsi : « {d} ».",
        "« {d} » : voici les mots de la courte description de {s}.",
        "Courte description : « {d} », pour {s}.",
        "« {d} » : faisons connaissance avec {s} à travers la courte description.",
    ),
    "es": (
        "{s} figura en la descripción breve como «{d}».",
        "«{d}»: estas son las palabras de la descripción breve de {s}.",
        "Descripción breve: «{d}», de {s}.",
        "«{d}»: conozcamos a {s} a través de la descripción breve.",
    ),
}

# Genre means only the existing selected metadata context for this track.
# Two forms per persona, with no musical properties or invented relationship.
GENRE = {
    "en": (
        (
            "Let’s look at the genre context of {t} by {a}: {g}.",
            "{a}, with {t}: the genre context here is {g}.",
        ),
        (
            "For {t} by {a}, the genre context is {g}.",
            "{g} is the genre context attached to {t} by {a}.",
        ),
        ("{t} — {a}. Genre context: {g}.", "Genre context, {g}; the track is {t} by {a}."),
        (
            "A glance at {t} by {a}: {g} is its genre context.",
            "{g} is on the genre-context line; the track is {t} by {a}.",
        ),
    ),
    "nl": (
        (
            "Even kijken: bij {t} van {a} hoort de genrecontext {g}.",
            "{a}, met {t}: de genrecontext hier is {g}.",
        ),
        (
            "Bij {t} van {a} is de genrecontext {g}.",
            "{g} is de genrecontext die bij {t} van {a} staat.",
        ),
        ("{t} — {a}. Genrecontext: {g}.", "Genrecontext, {g}; het nummer is {t} van {a}."),
        (
            "Een blik op {t} van {a}: {g} is de genrecontext.",
            "{g} staat bij de genrecontext; het gaat om {t} van {a}.",
        ),
    ),
    "de": (
        (
            "Bei „{t}“ von {a} schauen wir auf den Genrekontext: {g}.",
            "{a}, mit {t}: der Genrekontext hier ist {g}.",
        ),
        (
            "Bei {t} von {a} ist der Genrekontext {g}.",
            "{g} ist der Genrekontext, der bei {t} von {a} steht.",
        ),
        ("{t} — {a}. Genrekontext: {g}.", "Genrekontext, {g}; der Titel ist {t} von {a}."),
        (
            "Ein Blick auf {t} von {a}: {g} ist der Genrekontext.",
            "{g} steht beim Genrekontext; es geht um den Titel {t} von {a}.",
        ),
    ),
    "fr": (
        (
            "Regardons le contexte de genre du titre « {t} » de {a} : {g}.",
            "{a}, avec {t} : le contexte de genre ici est {g}.",
        ),
        (
            "Pour le titre « {t} » de {a}, le contexte de genre est {g}.",
            "{g} est le contexte de genre associé à {t} par {a}.",
        ),
        (
            "{t} — {a}. Contexte de genre : {g}.",
            "Contexte de genre, {g} ; le titre est {t} par {a}.",
        ),
        (
            "Un regard sur {t} par {a} : {g} est son contexte de genre.",
            "{g} figure dans le contexte de genre ; il s’agit du titre « {t} » de {a}.",
        ),
    ),
    "es": (
        (
            "Miremos el contexto de género de {t} de {a}: {g}.",
            "{a}, con {t}: el contexto de género aquí es {g}.",
        ),
        (
            "Para {t} de {a}, el contexto de género es {g}.",
            "{g} es el contexto de género asociado a {t} de {a}.",
        ),
        (
            "{t} — {a}. Contexto de género: {g}.",
            "Contexto de género, {g}; la canción es {t} de {a}.",
        ),
        (
            "Una mirada a {t} de {a}: {g} es su contexto de género.",
            "{g} figura en el contexto de género; se trata de {t} de {a}.",
        ),
    ),
}


def form_count(family: str) -> int:
    """Keep existing credits/callback four-form sequencing intact."""
    return 1 if family == "work_composers" else 2 if family in FACT_FAMILIES | {"genre_context", "album_continuity"} else 4


def genre_copy(
    *, locale: str, persona: str, form: int, genre: str, title: str, artist: str
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
    return GENRE[lang][PERSONAS.index(persona)][form % 2].format(g=genre, t=title, a=artist)


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
