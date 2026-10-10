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
BIRTH_ALTERNATE = {
    "en": (
        "{s} was born on the date recorded as {d}.",
        "{d} marks the recorded birth date of {s}.",
        "Birth date recorded: {d}, for {s}.",
        "Put {d} beside the name {s}: it is the recorded birth date.",
    ),
    "nl": (
        "Voor {s} staat {d} als geboortedatum genoteerd.",
        "{d} is de geregistreerde geboortedatum van {s}.",
        "Geboortedatum genoteerd: {d}, voor {s}.",
        "Zet {d} bij de naam {s}: dat is de vermelde geboortedatum.",
    ),
    "de": (
        "Für {s} ist {d} als Geburtsdatum vermerkt.",
        "{d} ist das verzeichnete Geburtsdatum von {s}.",
        "Verzeichnetes Geburtsdatum: {d}, für {s}.",
        "Setzen wir {d} neben den Namen {s}: das ist das verzeichnete Geburtsdatum.",
    ),
    "fr": (
        "Pour {s}, la date de naissance indiquée est {d}.",
        "{d} est la date de naissance indiquée pour {s}.",
        "Date de naissance indiquée : {d}, pour {s}.",
        "Plaçons {d} à côté du nom de {s} : c’est la date de naissance indiquée.",
    ),
    "es": (
        "Para {s}, la fecha de nacimiento registrada es {d}.",
        "{d} es la fecha de nacimiento registrada de {s}.",
        "Fecha de nacimiento registrada: {d}, de {s}.",
        "Pongamos {d} junto al nombre de {s}: es la fecha de nacimiento registrada.",
    ),
}
FORMATION_ALTERNATE = {
    "en": (
        "For {s}, the recorded formation date is {d}.",
        "{d} is the recorded formation date of {s}.",
        "Group formation recorded: {d}, for {s}.",
        "Back to the beginning of {s} as a group: the recorded formation date is {d}.",
    ),
    "nl": (
        "Voor {s} staat {d} als oprichtingsdatum genoteerd.",
        "{d} is de geregistreerde oprichtingsdatum van {s}.",
        "Oprichting van de groep genoteerd: {d}, voor {s}.",
        "Terug naar het begin van {s} als groep: de vermelde oprichtingsdatum is {d}.",
    ),
    "de": (
        "Für {s} ist {d} als Gründungsdatum vermerkt.",
        "{d} ist das verzeichnete Gründungsdatum von {s}.",
        "Gründung der Gruppe verzeichnet: {d}, für {s}.",
        "Zum Beginn von {s} als Gruppe: das verzeichnete Gründungsdatum ist {d}.",
    ),
    "fr": (
        "Pour {s}, la date de formation indiquée est {d}.",
        "{d} est la date de formation indiquée pour {s}.",
        "Formation du groupe indiquée : {d}, pour {s}.",
        "Aux débuts de {s} en tant que groupe : la date de formation indiquée est {d}.",
    ),
    "es": (
        "Para {s}, la fecha de formación registrada es {d}.",
        "{d} es la fecha de formación registrada de {s}.",
        "Formación del grupo registrada: {d}, de {s}.",
        "Volvamos al comienzo de {s} como grupo: la fecha de formación registrada es {d}.",
    ),
}
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
    return 2 if family in FACT_FAMILIES or family == "genre_context" else 4


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
